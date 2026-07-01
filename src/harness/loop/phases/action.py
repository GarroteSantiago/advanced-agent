"""Action phase: execute the tool calls the model requested."""

from __future__ import annotations

from harness.loop.phase import Outcome, PhaseResult
from harness.runtime import AgentExecutionContext
from harness.tools import ToolExecutor


class ActionPhase:
        """Runs each pending tool call and stashes the results on the context.

        Always reports ``ACTED``; folding results into the conversation is the
        observation phase's job.
        """

        def __init__(self, executor: ToolExecutor) -> None:
                self._executor = executor

        @property
        def name(self) -> str:
                return "action"

        async def run(self, context: AgentExecutionContext) -> PhaseResult:
                results = [
                        await self._executor.execute(call)
                        for call in context.pending_tool_calls()
                ]
                return PhaseResult(context.with_tool_results(results), Outcome.ACTED)
