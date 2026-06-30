"""The lifecycle states of a single agent execution."""

from __future__ import annotations

from enum import Enum, auto


class ExecutionState(Enum):
        """Where a run is in the reason -> act -> observe lifecycle.

        A plain enum, not a State-pattern object: transitions are owned by
        ``AgentExecutionContext``, so there is no per-state behavior to model.
        """

        IDLE = auto()
        REASONING = auto()
        ACTING = auto()
        OBSERVING = auto()
        COMPLETED = auto()
        ABORTED = auto()

        def is_terminal(self) -> bool:
                return self in (ExecutionState.COMPLETED, ExecutionState.ABORTED)
