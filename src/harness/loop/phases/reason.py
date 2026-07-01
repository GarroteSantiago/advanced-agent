"""Reason phase: ask the model what to do next."""

from __future__ import annotations

from harness.events import EventBus, ModelCalled
from harness.loop.phase import Outcome, PhaseResult
from harness.runtime import AgentExecutionContext
from harness.tools import ToolCatalog
from llm import ChatModel


class ReasonPhase:
        """Completes the conversation with the model and folds the turn in.

        Reports ``TOOLS_REQUESTED`` when the model wants tools, or ``ANSWERED``
        (a terminal answer) otherwise -- the navigator decides what each means.
        """

        def __init__(
                self,
                model: ChatModel,
                catalog: ToolCatalog,
                event_bus: EventBus | None = None,
        ) -> None:
                self._model = model
                self._catalog = catalog
                self._bus = event_bus or EventBus()

        @property
        def name(self) -> str:
                return "reason"

        async def run(self, context: AgentExecutionContext) -> PhaseResult:
                conversation = context.current_conversation()
                schemas = self._catalog.for_model()
                self._bus.publish(
                        ModelCalled(message_count=len(conversation), offered_tools=len(schemas))
                )

                completion = await self._model.complete(conversation, tools=schemas or None)
                context = context.with_assistant(completion)

                if completion.requests_tools():
                        return PhaseResult(context, Outcome.TOOLS_REQUESTED)
                return PhaseResult(context.stopped(completion.content), Outcome.ANSWERED)
