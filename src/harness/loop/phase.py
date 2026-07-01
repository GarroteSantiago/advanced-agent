"""The phase protocol, the result a phase returns, and the outcome vocabulary.

A phase advances the (immutable) context and reports an ``Outcome`` describing
what happened. It does not know which phase runs next -- that decision belongs
to the ``Navigator`` (see ``navigator``), which turns ``(phase, outcome)`` into
the successor. This keeps phases decoupled from one another and the loop a dumb
driver.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Protocol, runtime_checkable

from harness.runtime import AgentExecutionContext


class Outcome(Enum):
        """What a phase reports so the navigator can choose the next phase."""

        TOOLS_REQUESTED = auto()
        ANSWERED = auto()
        ACTED = auto()
        CONTINUE = auto()
        DENIED = auto()


@runtime_checkable
class Phase(Protocol):
        """One step of the cycle, run against the context."""

        @property
        def name(self) -> str: ...

        async def run(self, context: AgentExecutionContext) -> PhaseResult: ...


@dataclass(frozen=True, slots=True)
class PhaseResult:
        """A phase's output: the advanced context and what happened."""

        context: AgentExecutionContext
        outcome: Outcome
