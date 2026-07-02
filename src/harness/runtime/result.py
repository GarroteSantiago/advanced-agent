"""The terminal outcome of a run."""

from __future__ import annotations

from dataclasses import dataclass

from harness.runtime.context import AgentExecutionContext
from harness.runtime.ledger import TaskLedger
from harness.runtime.metadata import ExecutionMetadata
from harness.runtime.state import ExecutionState
from llm import Conversation


@dataclass(frozen=True, slots=True)
class ExecutionResult:
        """What a finished ``AgentLoop.run`` reports back.

        Carries the final ``conversation`` so a multi-turn session can persist
        history across user turns, and the final ``ledger`` so callers can read
        the shared task state (subagent results, sources, modified files).
        """

        final_output: str | None
        state: ExecutionState
        metadata: ExecutionMetadata
        conversation: Conversation
        ledger: TaskLedger
        stop_reason: str | None = None

        def succeeded(self) -> bool:
                return self.state is ExecutionState.COMPLETED

        @classmethod
        def from_context(
                cls,
                context: AgentExecutionContext,
                *,
                stop_reason: str | None = None,
        ) -> ExecutionResult:
                return cls(
                        final_output=context.final_output(),
                        state=context.state(),
                        metadata=context.metadata(),
                        conversation=context.current_conversation(),
                        ledger=context.ledger(),
                        stop_reason=stop_reason if stop_reason is not None else context.stop_reason(),
                )
