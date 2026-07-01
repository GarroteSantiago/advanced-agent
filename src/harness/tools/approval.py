"""Per-tool-call approval for tool execution.

The executor consults an ``Approver`` before invoking a tool. An approver returns
an ``Approval`` verdict (allow, or deny with a reason that becomes the tool
observation). Two kinds compose via ``CompositeApprover``:

- ``SupervisionPolicy`` -- human-in-the-loop: confirm mutating actions.
- ``PolicyVerifier`` (see ``policy``) -- config-driven deny/approval rules.

Lives in ``tools`` (not ``control``) because the executor consults it, and
``control`` already depends on ``runtime`` which depends on ``tools``.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from harness.tools.request import ToolRequest


@dataclass(frozen=True, slots=True)
class Approval:
        """A verdict on whether a tool invocation may proceed."""

        allowed: bool
        reason: str = ""

        @classmethod
        def allow(cls) -> Approval:
                return cls(allowed=True)

        @classmethod
        def deny(cls, reason: str) -> Approval:
                return cls(allowed=False, reason=reason)

        def denied(self) -> bool:
                return not self.allowed


@runtime_checkable
class Confirmer(Protocol):
        """Asks a human to confirm an action."""

        async def confirm(self, request: ToolRequest) -> bool: ...


@runtime_checkable
class Approver(Protocol):
        """Decides whether a tool invocation may proceed."""

        async def review(self, request: ToolRequest, *, mutating: bool) -> Approval: ...


class AutoApprover:
        """Approves everything -- the default when nothing gates execution."""

        async def review(self, request: ToolRequest, *, mutating: bool) -> Approval:
                return Approval.allow()


class SupervisionPolicy:
        """Approves read-only actions freely; when ``enabled``, asks a
        ``Confirmer`` before any mutating action. ``enabled`` is a public toggle."""

        def __init__(self, confirmer: Confirmer, *, enabled: bool = False) -> None:
                self._confirmer = confirmer
                self.enabled = enabled

        async def review(self, request: ToolRequest, *, mutating: bool) -> Approval:
                if not (self.enabled and mutating):
                        return Approval.allow()
                if await self._confirmer.confirm(request):
                        return Approval.allow()
                return Approval.deny("declined by the user")


class CompositeApprover:
        """Consults approvers in order; the first denial wins (fail-closed)."""

        def __init__(self, approvers: Iterable[Approver]) -> None:
                self._approvers: tuple[Approver, ...] = tuple(approvers)

        async def review(self, request: ToolRequest, *, mutating: bool) -> Approval:
                for approver in self._approvers:
                        verdict = await approver.review(request, mutating=mutating)
                        if verdict.denied():
                                return verdict
                return Approval.allow()
