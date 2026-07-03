"""Forced synthesis: turning an unfinished run into usable partial findings.

When a subagent's loop halts without a final answer -- capped by the iteration
limiter or stopped for stalling -- its raw stop-reason ("reached the iteration
cap of 8") is useless to the principal, and every observation it gathered is
thrown away. ``PartialSynthesizer`` runs one final, tool-less model turn over
the accumulated conversation, asking the model to report what it found and what
remains blocked. This is how the spec's "when blocked, explain what was tried
and what is missing" is honoured, and how a capped subagent still contributes.

It emits the same ``ModelCalled``/``ModelCompleted`` events a reason turn does,
so this extra call stays visible in the trace and its cost is accounted for. The
event/timing/pricing block is a small, deliberate duplication of ``ReasonPhase``;
if a third caller appears it is worth extracting an "observed model" decorator.
"""

from __future__ import annotations

from time import perf_counter

from harness.events import EventBus, ModelCalled, ModelCompleted
from llm import ChatModel, Conversation, Message, estimate_cost


class PartialSynthesizer:
        """Asks the model to recap findings and blockers when a run does not finish."""

        _INSTRUCTION = (
                "You did not finish the task. Do not call any tools. In prose, summarize "
                "concisely what you found so far and what remains unresolved or blocked."
        )

        def __init__(self, model: ChatModel, event_bus: EventBus | None = None) -> None:
                self._model = model
                self._bus = event_bus or EventBus()

        async def summarize(self, conversation: Conversation) -> str:
                prompt = conversation.with_message(Message.user(self._INSTRUCTION))
                model = self._model.identifier()
                self._bus.publish(
                        ModelCalled(message_count=len(prompt), offered_tools=0, model=model)
                )

                started = perf_counter()
                completion = await self._model.complete(prompt, tools=None)
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
                return completion.content
