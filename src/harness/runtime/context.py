"""The shared execution spine.

``AgentExecutionContext`` is the single object every phase reads from and writes
to. It is immutable: each transition (``with_assistant``, ``with_tool_results``,
``observed``, ``stopped``, ``aborted``) returns a new context, so a phase can
never corrupt state for another and the conversation/observations are never
exposed as mutable lists. This is the anti-anemic heart of the runtime.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace

from harness.runtime.ledger import Source, SubagentResult, TaskLedger
from harness.runtime.metadata import ExecutionMetadata
from harness.runtime.state import ExecutionState
from harness.tools import ToolResult
from llm import Completion, Conversation, Message, ToolCall


@dataclass(frozen=True, slots=True)
class AgentExecutionContext:
        """Immutable task state threaded through the agent loop."""

        _conversation: Conversation
        _metadata: ExecutionMetadata
        _ledger: TaskLedger
        _state: ExecutionState = ExecutionState.IDLE
        _pending: tuple[ToolCall, ...] = ()
        _last_results: tuple[ToolResult, ...] = ()
        _final_output: str | None = None
        _stop_reason: str | None = None
        _cycle_signatures: tuple[str, ...] = ()

        @classmethod
        def for_task(
                cls,
                task_id: str,
                conversation: Conversation,
                *,
                request: str = "",
        ) -> AgentExecutionContext:
                return cls(
                        _conversation=conversation,
                        _metadata=ExecutionMetadata(task_id=task_id),
                        _ledger=TaskLedger.for_request(request),
                )

        # --- queries -------------------------------------------------------
        def current_conversation(self) -> Conversation:
                return self._conversation

        def pending_tool_calls(self) -> Sequence[ToolCall]:
                return self._pending

        def has_pending_actions(self) -> bool:
                return bool(self._pending)

        def state(self) -> ExecutionState:
                return self._state

        def metadata(self) -> ExecutionMetadata:
                return self._metadata

        def ledger(self) -> TaskLedger:
                return self._ledger

        def final_output(self) -> str | None:
                return self._final_output

        def stop_reason(self) -> str | None:
                return self._stop_reason

        def cycle_signature(self) -> str:
                """A stable fingerprint of the current action+observation.

                The hook the (deferred) ``ProgressTracker`` uses to notice the
                agent repeating the same call and getting the same result.
                """
                calls = ";".join(
                        f"{call.name}({sorted(call.arguments.items(), key=lambda kv: kv[0])})"
                        for call in self._pending
                )
                results = ";".join(
                        f"{result.tool_name}:{result.ok}:{result.content}"
                        for result in self._last_results
                )
                return f"{calls}=>{results}"

        def recorded_signatures(self) -> Sequence[str]:
                """The signature of every cycle closed so far.

                The history a progress tracker reads to notice the agent
                repeating the same call/result without making progress.
                """
                return self._cycle_signatures

        # --- transitions (copy-on-write) -----------------------------------
        def with_assistant(self, completion: Completion) -> AgentExecutionContext:
                # A model turn is one loop pass: it advances the iteration count
                # and accumulates the call's token usage.
                message = Message.assistant(completion.content, completion.tool_calls)
                return replace(
                        self,
                        _conversation=self._conversation.with_message(message),
                        _pending=completion.tool_calls,
                        _metadata=self._metadata.add_usage(completion.usage).incremented(),
                        _state=ExecutionState.REASONING,
                )

        def with_tool_results(self, results: Iterable[ToolResult]) -> AgentExecutionContext:
                return replace(
                        self,
                        _last_results=tuple(results),
                        _state=ExecutionState.ACTING,
                )

        def observed(self) -> AgentExecutionContext:
                """Fold tool results into the conversation and close the cycle.

                Does not advance the iteration count -- that belongs to the model
                turn (``with_assistant``), so one iteration == one model call.
                """
                folded = self._conversation.with_messages(
                        result.to_message() for result in self._last_results
                )
                return replace(
                        self,
                        _conversation=folded,
                        _cycle_signatures=(*self._cycle_signatures, self.cycle_signature()),
                        _pending=(),
                        _last_results=(),
                        _state=ExecutionState.OBSERVING,
                )

        def stopped(self, output: str) -> AgentExecutionContext:
                return replace(
                        self,
                        _final_output=output,
                        _state=ExecutionState.COMPLETED,
                        _stop_reason="model produced a final answer",
                )

        def aborted(self, reason: str = "") -> AgentExecutionContext:
                return replace(self, _state=ExecutionState.ABORTED, _stop_reason=reason or None)

        def advised(self, note: str) -> AgentExecutionContext:
                """Fold harness steering into the conversation (loop-break guidance).

                Injected as a user-role message so the next reason turn reads it as
                feedback. The harness speaks here, not the human, but user-role is
                the portable way to steer a chat model mid-run.
                """
                return replace(
                        self,
                        _conversation=self._conversation.with_message(Message.user(note)),
                        _state=ExecutionState.OBSERVING,
                )

        # --- ledger transitions (delegate to the shared task state) ---------
        def noting_progress(self, note: str) -> AgentExecutionContext:
                return replace(self, _ledger=self._ledger.with_progress(note))

        def crediting(self, result: SubagentResult) -> AgentExecutionContext:
                return replace(self, _ledger=self._ledger.with_subagent_result(result))

        def consulting(self, source: Source) -> AgentExecutionContext:
                return replace(self, _ledger=self._ledger.with_source(source))

        def touching(self, path: str) -> AgentExecutionContext:
                return replace(self, _ledger=self._ledger.with_modified_file(path))

        def touching_all(self, paths: Iterable[str]) -> AgentExecutionContext:
                """Record several modified files at once (no-op for an empty run).

                The batch form the action phases use to fold the paths a cycle's
                tools reported into the ledger in one copy-on-write step.
                """
                ledger = self._ledger
                for path in paths:
                        ledger = ledger.with_modified_file(path)
                if ledger is self._ledger:
                        return self
                return replace(self, _ledger=ledger)

        def observing_that(self, note: str) -> AgentExecutionContext:
                return replace(self, _ledger=self._ledger.with_observation(note))
