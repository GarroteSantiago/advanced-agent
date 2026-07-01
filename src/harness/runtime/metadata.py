"""Per-run bookkeeping: iteration count and token usage."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime

from llm import TokenUsage


def _now() -> datetime:
        return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class ExecutionMetadata:
        """Immutable run bookkeeping; each update returns a new metadata."""

        task_id: str
        iterations: int = 0
        usage: TokenUsage = field(default_factory=TokenUsage)
        started_at: datetime = field(default_factory=_now)

        def incremented(self) -> ExecutionMetadata:
                return replace(self, iterations=self.iterations + 1)

        def add_usage(self, usage: TokenUsage) -> ExecutionMetadata:
                return replace(self, usage=self.usage + usage)
