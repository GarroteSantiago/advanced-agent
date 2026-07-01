"""Unit tests for the Navigator: the phase graph as an inspectable object.

The whole point of the navigator is that the graph is testable in isolation,
without running any phase.
"""

import pytest

from harness.loop import (
        Continue,
        Halt,
        Navigator,
        Outcome,
        PhaseResult,
        UnknownTransitionError,
)
from harness.runtime import AgentExecutionContext


class _DummyPhase:
        def __init__(self, name: str) -> None:
                self._name = name

        @property
        def name(self) -> str:
                return self._name

        async def run(self, context: AgentExecutionContext) -> PhaseResult:
                raise NotImplementedError  # the navigator never runs phases


def test_navigator_continues_to_the_mapped_phase():
        a, b = _DummyPhase("a"), _DummyPhase("b")
        navigator = Navigator(
                start=a,
                transitions={
                        (a, Outcome.ACTED): Continue(b),
                        (b, Outcome.ANSWERED): Halt(),
                },
        )

        assert navigator.start() is a

        transition = navigator.next(a, Outcome.ACTED)
        assert isinstance(transition, Continue)
        assert transition.phase is b


def test_navigator_halts_on_a_terminal_edge():
        a = _DummyPhase("a")
        navigator = Navigator(start=a, transitions={(a, Outcome.ANSWERED): Halt()})

        assert isinstance(navigator.next(a, Outcome.ANSWERED), Halt)


def test_navigator_raises_on_an_unmapped_transition():
        a = _DummyPhase("a")
        navigator = Navigator(start=a, transitions={})

        with pytest.raises(UnknownTransitionError) as excinfo:
                navigator.next(a, Outcome.ACTED)
        assert excinfo.value.outcome is Outcome.ACTED
