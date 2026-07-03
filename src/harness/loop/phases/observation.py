"""Observation phase: integrate results and decide whether to continue."""

from __future__ import annotations

from harness.control import Controller, ProgressTracker
from harness.events import CycleCompleted, EventBus, GuardTripped, StrategyNudged
from harness.loop.phase import Outcome, PhaseResult
from harness.runtime import AgentExecutionContext


class ObservationPhase:
        """Folds tool results into the conversation, closes the cycle, and decides
        whether the run may continue.

        Two collaborators gate the decision, in order of severity: the
        ``Controller`` (hard limits -- iteration cap, policy) can outright deny,
        and an optional ``ProgressTracker`` catches the softer "repeating without
        progress" case, nudging once before it stops. Reports ``CONTINUE`` when
        the run proceeds (with or without a nudge folded in), or ``DENIED``
        (recording the reason on the context) when a limit or a stall halts it.
        """

        def __init__(
                self,
                controller: Controller,
                event_bus: EventBus | None = None,
                tracker: ProgressTracker | None = None,
        ) -> None:
                self._controller = controller
                self._bus = event_bus or EventBus()
                self._tracker = tracker

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

                if self._tracker is not None:
                        return self._weigh_progress(context)
                return PhaseResult(context, Outcome.CONTINUE)

        def _weigh_progress(self, context: AgentExecutionContext) -> PhaseResult:
                assert self._tracker is not None
                assessment = self._tracker.assess(context)

                if assessment.stalled():
                        self._bus.publish(GuardTripped(guard=self._tracker.name, reason=assessment.reason))
                        return PhaseResult(context.aborted(assessment.reason), Outcome.DENIED)

                if assessment.stalling():
                        signatures = context.recorded_signatures()
                        occurrences = signatures.count(signatures[-1])
                        self._bus.publish(StrategyNudged(reason=assessment.reason, occurrences=occurrences))
                        return PhaseResult(context.advised(_nudge(assessment.reason)), Outcome.CONTINUE)

                return PhaseResult(context, Outcome.CONTINUE)


def _nudge(reason: str) -> str:
        return (
                "You have repeated the same action and received the same result. "
                "Repeating it will not make progress. Use what you already have to "
                "proceed differently, or give your final answer now. "
                f"(harness: {reason})"
        )
