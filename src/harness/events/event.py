"""Domain events emitted by the harness during a run.

Events are immutable facts about what happened ("a phase started", "a tool was
observed"). They are the substrate for observability: an ``AuditLogger`` (or, in
a later increment, a Langfuse/Phoenix adapter) subscribes to the bus and turns
this stream into a trace. Every event is keyword-constructed and timestamped at
creation.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime


def _now() -> datetime:
        return datetime.now(UTC)


@dataclass(frozen=True, slots=True, kw_only=True)
class Event:
        """Base class for all harness events.

        ``source`` names the agent that emitted the event: empty for the principal,
        the subagent's name once an ``EventForwarder`` bridges a subagent's private
        stream onto the principal bus. It is how aggregated observability keeps the
        provenance a nested trace needs.
        """

        occurred_at: datetime = field(default_factory=_now)
        source: str = ""


@dataclass(frozen=True, slots=True, kw_only=True)
class PhaseStarted(Event):
        phase: str


@dataclass(frozen=True, slots=True, kw_only=True)
class PhaseCompleted(Event):
        phase: str


@dataclass(frozen=True, slots=True, kw_only=True)
class ModelCalled(Event):
        message_count: int
        offered_tools: int
        model: str = ""


@dataclass(frozen=True, slots=True, kw_only=True)
class ModelCompleted(Event):
        model: str
        prompt_tokens: int
        completion_tokens: int
        latency_ms: float
        cost_usd: float
        output: str = ""


@dataclass(frozen=True, slots=True, kw_only=True)
class ToolInvoked(Event):
        tool_name: str
        call_id: str
        arguments: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True, kw_only=True)
class ToolObserved(Event):
        tool_name: str
        call_id: str
        ok: bool
        error: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class DocumentsRetrieved(Event):
        query: str
        sources: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class CycleCompleted(Event):
        iteration: int


@dataclass(frozen=True, slots=True, kw_only=True)
class LoopStopped(Event):
        reason: str
        output: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class GuardTripped(Event):
        guard: str
        reason: str


@dataclass(frozen=True, slots=True, kw_only=True)
class StrategyNudged(Event):
        """A no-progress loop was detected and corrective guidance was injected."""

        reason: str
        occurrences: int
