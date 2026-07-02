"""Reason phase: ask the model what to do next."""

from __future__ import annotations

from time import perf_counter

from harness.events import EventBus, ModelCalled, ModelCompleted
from harness.loop.phase import Outcome, PhaseResult
from harness.runtime import AgentExecutionContext
from harness.tools import ToolCatalog
from llm import ChatModel, estimate_cost


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
                model = self._model.identifier()
                self._bus.publish(
                        ModelCalled(
                                message_count=len(conversation),
                                offered_tools=len(schemas),
                                model=model,
                        )
                )

                started = perf_counter()
                completion = await self._model.complete(conversation, tools=schemas or None)
                latency_ms = (perf_counter() - started) * 1000
                self._bus.publish(
                        ModelCompleted(
                                model=model,
                                prompt_tokens=completion.usage.prompt_tokens,
                                completion_tokens=completion.usage.completion_tokens,
                                latency_ms=latency_ms,
                                cost_usd=estimate_cost(model, completion.usage),
                                output=completion.content,
                        )
                )
                context = context.with_assistant(completion)

                if completion.requests_tools():
                        return PhaseResult(context, Outcome.TOOLS_REQUESTED)
                return PhaseResult(context.stopped(completion.content), Outcome.ANSWERED)
