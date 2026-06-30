"""The agent loop: a dumb driver over phases and a navigator.

The loop reads as its intent: start at the navigator's first phase, and while
there is a phase, run it and ask the navigator what comes next. All routing
lives in the navigator; all mutable state lives in the immutable context. The
loop neither knows the graph nor holds run state.
"""

from __future__ import annotations

from harness.events import EventBus, LoopStopped, PhaseCompleted, PhaseStarted
from harness.loop.navigator import Continue, Navigator, Transition
from harness.loop.phase import Phase, PhaseResult
from harness.runtime import AgentExecutionContext, ExecutionResult


class AgentLoop:
        """Drives phases until the navigator says the run is over."""

        def __init__(self, navigator: Navigator, event_bus: EventBus | None = None) -> None:
                self._navigator = navigator
                self._bus = event_bus or EventBus()

        async def step(self, context: AgentExecutionContext, phase: Phase) -> PhaseResult:
                """Run a single phase, bracketed by start/complete events."""
                self._bus.publish(PhaseStarted(phase=phase.name))
                result = await phase.run(context)
                self._bus.publish(PhaseCompleted(phase=phase.name))
                return result

        async def run(self, context: AgentExecutionContext) -> ExecutionResult:
                # Python's "while let Continue(phase) = ...": loop while the
                # navigator keeps saying Continue; a Halt ends it.
                transition: Transition = Continue(self._navigator.start())
                while isinstance(transition, Continue):
                        phase = transition.phase
                        result = await self.step(context, phase)
                        context = result.context
                        transition = self._navigator.next(phase, result.outcome)
                self._bus.publish(
                        LoopStopped(reason=context.stop_reason() or "", output=context.final_output())
                )
                return ExecutionResult.from_context(context)
