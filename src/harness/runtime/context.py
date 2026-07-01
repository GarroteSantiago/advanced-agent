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

from harness.runtime.metadata import ExecutionMetadata
from harness.runtime.state import ExecutionState
from harness.tools import ToolResult
from llm import Completion, Conversation, Message, ToolCall


@dataclass(frozen=True, slots=True)
class AgentExecutionContext:
        """Immutable task state threaded through the agent loop."""

        _conversation: Conversation
        _metadata: ExecutionMetadata
        _state: ExecutionState = ExecutionState.IDLE
        _pending: tuple[ToolCall, ...] = ()
        _last_results: tuple[ToolResult, ...] = ()
        _final_output: str | None = None
        _stop_reason: str | None = None

        @classmethod
        def for_task(cls, task_id: str, conversation: Conversation) -> AgentExecutionContext:
                return cls(_conversation=conversation, _metadata=ExecutionMetadata(task_id=task_id))

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
