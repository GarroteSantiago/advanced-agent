"""Observation phase: integrate results and decide whether to continue."""

from __future__ import annotations

from harness.control import Controller
from harness.events import CycleCompleted, EventBus, GuardTripped
from harness.loop.phase import Outcome, PhaseResult
from harness.runtime import AgentExecutionContext


class ObservationPhase:
        """Folds tool results into the conversation, closes the cycle, and asks
        the controller whether the run may continue.

        Reports ``CONTINUE`` when permitted, or ``DENIED`` (recording the reason
        on the context) when a guard stops the run.
        """

        def __init__(self, controller: Controller, event_bus: EventBus | None = None) -> None:
                self._controller = controller
                self._bus = event_bus or EventBus()

        @property
        def name(self) -> str:
                return "observation"

        async def run(self, context: AgentExecutionContext) -> PhaseResult:
                context = context.observed()
                self._bus.publish(CycleCompleted(iteration=context.metadata().iterations))

                decision = self._controller.permit(context)
                if decision.denied():
                        self._bus.publish(GuardTripped(guard="controller", reason=decision.reason))
                        return PhaseResult(context.aborted(decision.reason), Outcome.DENIED)
                return PhaseResult(context, Outcome.CONTINUE)
