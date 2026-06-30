"""Executes a model's tool call against the registered tools.

The executor is the single collaborator the action phase touches. It resolves
the tool, builds a request, invokes it, and -- crucially -- turns every failure
(unknown tool, or an exception raised inside a tool) into a ``ToolResult`` so the
loop always has an observation to feed back to the model. It narrates its work
on the event bus.
"""

from __future__ import annotations

from harness.events import EventBus, ToolInvoked, ToolObserved
from harness.tools.approval import Approver, AutoApprover
from harness.tools.registry import ToolRegistry, UnknownToolError
from harness.tools.request import ToolRequest
from harness.tools.result import ToolResult
from llm import ToolCall


class ToolExecutor:
        """Turns a ``ToolCall`` into a ``ToolResult``, never raising on tool failure.

        Before invoking a tool it consults an ``Approver``; with the default
        ``AutoApprover`` everything runs, but a ``SupervisionPolicy`` can gate
        mutating tools behind user confirmation.
        """

        def __init__(
                self,
                registry: ToolRegistry,
                event_bus: EventBus | None = None,
                approver: Approver | None = None,
        ) -> None:
                self._registry = registry
                self._bus = event_bus or EventBus()
                self._approver = approver or AutoApprover()

        async def execute(self, call: ToolCall) -> ToolResult:
                self._bus.publish(
                        ToolInvoked(tool_name=call.name, call_id=call.id, arguments=call.arguments)
                )
                result = await self._run(call)
                self._bus.publish(
                        ToolObserved(tool_name=call.name, call_id=call.id, ok=result.ok)
                )
                return result

        async def _run(self, call: ToolCall) -> ToolResult:
                try:
                        tool = self._registry.get(call.name)
                except UnknownToolError as error:
                        return ToolResult.failure(
                                call_id=call.id,
                                tool_name=call.name,
                                error=str(error),
                        )

                request = ToolRequest(
                        call_id=call.id,
                        tool_name=call.name,
                        arguments=call.arguments,
                )

                verdict = await self._approver.review(request, mutating=tool.mutates)
                if verdict.denied():
                        return ToolResult.failure(
                                call_id=call.id,
                                tool_name=call.name,
                                error=verdict.reason,
                        )

                try:
                        return await tool.invoke(request)
                except Exception as error:
                        # Boundary: any fault inside a tool becomes an observation,
                        # never an exception that escapes the loop.
                        return ToolResult.failure(
                                call_id=call.id,
                                tool_name=call.name,
                                error=f"{type(error).__name__}: {error}",
                        )
