"""The verdict a guard (or the controller) returns."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Decision:
        """Whether the run may proceed, and why not when it may not."""

        allowed: bool
        reason: str = ""

        @classmethod
        def allow(cls) -> Decision:
                return cls(allowed=True)

        @classmethod
        def deny(cls, reason: str) -> Decision:
                return cls(allowed=False, reason=reason)

        def denied(self) -> bool:
                return not self.allowed
