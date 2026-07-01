"""The guard port.

A guard inspects the execution context and rules on whether the run may
continue. Guards are how the harness stays "trustworthy, auditable, and
contained": limits, policy checks, and (later) progress/loop detection all
implement this one interface, so the controller composes them uniformly.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from harness.control.decision import Decision
from harness.runtime import AgentExecutionContext


@runtime_checkable
class Guard(Protocol):
        @property
        def name(self) -> str: ...

        def evaluate(self, context: AgentExecutionContext) -> Decision: ...
