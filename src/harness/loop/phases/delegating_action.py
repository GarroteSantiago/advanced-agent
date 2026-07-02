"""Delegating action phase: run tool calls, but route subagent calls to the team.

Used only by the *principal* loop. For each pending call it either delegates to
a subagent (merging the returned ``SubagentReport`` into the shared ``TaskLedger``
and folding the subagent's answer back as the tool observation) or runs an
ordinary tool through the executor. Subagents run the plain ``ActionPhase``, so
they receive no delegation calls -- delegation cannot recurse.
"""

from __future__ import annotations

from harness.delegation import SubagentRegistry, SubagentReport
from harness.events import EventBus, ToolInvoked, ToolObserved
from harness.loop.phase import Outcome, PhaseResult
from harness.runtime import AgentExecutionContext, SubagentResult
from harness.tools import ToolExecutor, ToolResult
from llm import ToolCall


class DelegatingActionPhase:
        """Executes tools and subagent delegations, recording both."""

        def __init__(
                self,
                executor: ToolExecutor,
                subagents: SubagentRegistry,
                event_bus: EventBus | None = None,
        ) -> None:
                self._executor = executor
                self._subagents = subagents
                self._bus = event_bus or EventBus()

        @property
        def name(self) -> str:
                return "action"

        async def run(self, context: AgentExecutionContext) -> PhaseResult:
                results: list[ToolResult] = []
                for call in context.pending_tool_calls():
                        if self._subagents.knows(call.name):
                                context, result = await self._run_delegation(context, call)
                        else:
                                result = await self._executor.execute(call)
                        results.append(result)
                return PhaseResult(context.with_tool_results(results), Outcome.ACTED)

        async def _run_delegation(
                self, context: AgentExecutionContext, call: ToolCall
        ) -> tuple[AgentExecutionContext, ToolResult]:
                task = str(call.arguments.get("task", ""))
                self._bus.publish(
                        ToolInvoked(tool_name=call.name, call_id=call.id, arguments=call.arguments)
                )
                report = await self._subagents.resolve(call.name).delegate(task)
                context = self._merge(context, report)
                self._bus.publish(
                        ToolObserved(
                                tool_name=call.name,
                                call_id=call.id,
                                ok=report.succeeded,
                                error=None if report.succeeded else report.output,
                        )
                )
                return context, _result_of(call, report)

        def _merge(
                self, context: AgentExecutionContext, report: SubagentReport
        ) -> AgentExecutionContext:
                context = context.crediting(
                        SubagentResult(report.agent, report.output, report.succeeded)
                )
                for source in report.sources:
                        context = context.consulting(source)
                for path in report.modified_files:
                        context = context.touching(path)
                for note in report.observations:
                        context = context.observing_that(note)
                return context


def _result_of(call: ToolCall, report: SubagentReport) -> ToolResult:
        if report.succeeded:
                return ToolResult.success(
                        call_id=call.id, tool_name=call.name, content=report.output
                )
        return ToolResult.failure(call_id=call.id, tool_name=call.name, error=report.output)
