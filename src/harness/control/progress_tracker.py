"""No-progress loop detection over the recorded cycle signatures.

Unlike a ``Guard`` -- whose ``Decision`` is a binary go/no-go -- the tracker
grades repetition, because the harness responds to a loop in two steps rather
than one: the first repeated cycle earns a *nudge* (a chance to change strategy),
and a further repeat *stops* the run. That third state (``STALLING``) is why the
tracker is its own collaborator instead of a guard folded into the controller;
the controller stays purely about hard limits.

The tracker is a pure function of the context: all state (the signature history)
lives on the immutable ``AgentExecutionContext``, so a single tracker instance is
safe to reuse across delegations without leaking one run's history into the next.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from harness.runtime import AgentExecutionContext

_EMPTY_SIGNATURE = "=>"


class Progress(Enum):
        """How the run is faring against repetition."""

        ADVANCING = auto()
        STALLING = auto()
        STALLED = auto()


@dataclass(frozen=True, slots=True)
class ProgressAssessment:
        """The tracker's verdict on the latest cycle, and why."""

        progress: Progress
        reason: str = ""

        def advancing(self) -> bool:
                return self.progress is Progress.ADVANCING

        def stalling(self) -> bool:
                return self.progress is Progress.STALLING

        def stalled(self) -> bool:
                return self.progress is Progress.STALLED


class ProgressTracker:
        """Flags the agent repeating the same action and getting the same result.

        ``stall_at`` and ``stop_at`` are occurrence counts of the *latest* cycle
        signature within the history: reaching ``stall_at`` nudges, reaching
        ``stop_at`` halts. The defaults (2, 3) give the model exactly one
        corrective turn between the first repeat and the stop.
        """

        def __init__(self, *, stall_at: int = 2, stop_at: int = 3) -> None:
                if stall_at < 2:
                        raise ValueError("stall_at must be at least 2 (1 is not yet a repeat)")
                if stop_at <= stall_at:
                        raise ValueError("stop_at must exceed stall_at")
                self._stall_at = stall_at
                self._stop_at = stop_at

        @property
        def name(self) -> str:
                return "progress-tracker"

        def assess(self, context: AgentExecutionContext) -> ProgressAssessment:
                signatures = context.recorded_signatures()
                if not signatures:
                        return ProgressAssessment(Progress.ADVANCING)

                latest = signatures[-1]
                if latest == _EMPTY_SIGNATURE:
                        return ProgressAssessment(Progress.ADVANCING)

                occurrences = sum(1 for signature in signatures if signature == latest)
                if occurrences >= self._stop_at:
                        reason = self._reason(occurrences, stopping=True)
                        return ProgressAssessment(Progress.STALLED, reason)
                if occurrences >= self._stall_at:
                        reason = self._reason(occurrences, stopping=False)
                        return ProgressAssessment(Progress.STALLING, reason)
                return ProgressAssessment(Progress.ADVANCING)

        def _reason(self, occurrences: int, *, stopping: bool) -> str:
                tail = "stopping the run" if stopping else "a change of strategy is needed"
                return (
                        f"{self.name}: the same action and result repeated {occurrences} times "
                        f"without progress -- {tail}"
                )
