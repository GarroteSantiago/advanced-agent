"""A guard that caps the number of reason/act/observe cycles."""

from __future__ import annotations

from harness.control.decision import Decision
from harness.runtime import AgentExecutionContext


class IterationLimiter:
        """Denies once the run has performed ``max_iterations`` cycles.

        The hard backstop against runaway loops; the (deferred) ``ProgressTracker``
        will add the softer "repeating without progress" detection.
        """

        def __init__(self, max_iterations: int) -> None:
                if max_iterations < 1:
                        raise ValueError("max_iterations must be at least 1")
                self._max = max_iterations

        @property
        def name(self) -> str:
                return "iteration-limiter"

        def evaluate(self, context: AgentExecutionContext) -> Decision:
                if context.metadata().iterations >= self._max:
                        return Decision.deny(
                                f"{self.name}: reached the iteration cap of {self._max}"
                        )
                return Decision.allow()
