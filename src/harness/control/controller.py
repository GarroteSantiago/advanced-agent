"""Composes guards into a single go/no-go decision.

``Controller`` is the typed replacement for the old untyped ``running_strategy``:
the loop asks it ``permit`` before continuing, and it returns the first denial
(fail-closed). Guards are evaluated in registration order.
"""

from __future__ import annotations

from collections.abc import Iterable

from harness.control.decision import Decision
from harness.control.guard import Guard
from harness.runtime import AgentExecutionContext


class Controller:
        """Asks each guard in turn; the first to deny stops the run."""

        def __init__(self, guards: Iterable[Guard] = ()) -> None:
                self._guards: tuple[Guard, ...] = tuple(guards)

        def permit(self, context: AgentExecutionContext) -> Decision:
                for guard in self._guards:
                        decision = guard.evaluate(context)
                        if decision.denied():
                                return decision
                return Decision.allow()
