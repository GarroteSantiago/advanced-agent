"""Control: limits and verification that keep a run contained and auditable.

Implemented now: ``Decision``, the ``Guard`` port, ``IterationLimiter``, the
``Controller`` that composes guards, and ``ProgressTracker``. The tracker is
deliberately *not* a ``Guard``: its verdict is three-valued (advancing /
stalling / stalled) so the loop can nudge before it stops, which a binary
go/no-go cannot express. Deferred guard seams (``BudgetLimiter``,
``ApprovalPolicy``) will implement the ``Guard`` interface and need no loop change.
"""

from harness.control.controller import Controller
from harness.control.decision import Decision
from harness.control.guard import Guard
from harness.control.iteration_limiter import IterationLimiter
from harness.control.progress_tracker import Progress, ProgressAssessment, ProgressTracker

__all__ = [
        "Controller",
        "Decision",
        "Guard",
        "IterationLimiter",
        "Progress",
        "ProgressAssessment",
        "ProgressTracker",
]
