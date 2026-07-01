"""The navigator: the phase graph as one explicit, testable transition table.

The loop asks the navigator where to go next given the phase that just ran and
the outcome it reported. The navigator's answer is a ``Transition`` -- either
``Continue(next_phase)`` or ``Halt`` -- so termination is decided here, in one
place, without a ``None`` sentinel. The whole graph (continuing edges *and*
exits) stays visible in the table built at the composition root. An unmapped
``(phase, outcome)`` is a wiring bug, so it fails loudly.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from harness.loop.phase import Outcome, Phase


class Transition:
        """A navigator's answer. Sealed: ``Continue`` or ``Halt``."""

        __slots__ = ()


@dataclass(frozen=True, slots=True)
class Continue(Transition):
        """Keep going: run ``phase`` next."""

        phase: Phase


@dataclass(frozen=True, slots=True)
class Halt(Transition):
        """End the run. The terminal reason lives on the context (set by the
        phase via ``stopped``/``aborted``); this is a pure control marker."""


class UnknownTransitionError(Exception):
        """Raised when no edge is defined for a ``(phase, outcome)`` pair."""

        def __init__(self, phase: Phase, outcome: Outcome) -> None:
                super().__init__(
                        f"no transition from phase {phase.name!r} on outcome {outcome.name}"
                )
                self.phase = phase
                self.outcome = outcome


class Navigator:
        """Maps ``(current phase, outcome)`` to a ``Transition``."""

        def __init__(
                self,
                start: Phase,
                transitions: Mapping[tuple[Phase, Outcome], Transition],
        ) -> None:
                self._start = start
                self._transitions: dict[tuple[Phase, Outcome], Transition] = dict(transitions)

        def start(self) -> Phase:
                return self._start

        def next(self, current: Phase, outcome: Outcome) -> Transition:
                key = (current, outcome)
                if key not in self._transitions:
                        raise UnknownTransitionError(current, outcome)
                return self._transitions[key]
