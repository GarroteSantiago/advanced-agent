"""Pure mapping from harness events to span data.

This module has NO external dependency: it turns our domain events into a
provider-neutral ``SpanData`` (a name + OpenInference-style attributes). The
Phoenix/OpenTelemetry boundary (``observability.phoenix``) consumes these and
creates real spans. Keeping the mapping pure is what makes observability
unit-testable without installing Phoenix -- the same split ``OpenAIChatModel``
uses (pure ``encode``/``decode`` + a thin SDK boundary).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from harness.events import ModelCalled, ModelCompleted, ToolInvoked, ToolObserved

# OpenInference semantic-convention attribute keys (stable strings, so the pure
# module needs no dependency on the conventions package).
SPAN_KIND = "openinference.span.kind"


@dataclass(frozen=True, slots=True)
class SpanData:
        """A provider-neutral description of one span."""

        name: str
        attributes: Mapping[str, object]


def _agent(source: str) -> str:
        """The emitting agent's name; empty source is the principal coordinator."""
        return source or "principal"


def llm_span(called: ModelCalled, completed: ModelCompleted) -> SpanData:
        total = completed.prompt_tokens + completed.completion_tokens
        return SpanData(
                name=f"llm {completed.model}",
                attributes={
                        SPAN_KIND: "LLM",
                        "agent.name": _agent(completed.source),
                        "llm.model_name": completed.model,
                        "llm.token_count.prompt": completed.prompt_tokens,
                        "llm.token_count.completion": completed.completion_tokens,
                        "llm.token_count.total": total,
                        "llm.latency_ms": completed.latency_ms,
                        "llm.cost.total_usd": completed.cost_usd,
                        "llm.input_message_count": called.message_count,
                        "output.value": completed.output,
                },
        )


def tool_span(invoked: ToolInvoked, observed: ToolObserved) -> SpanData:
        attributes: dict[str, object] = {
                SPAN_KIND: "TOOL",
                "agent.name": _agent(invoked.source),
                "tool.name": invoked.tool_name,
                "tool.call_id": invoked.call_id,
                "input.value": _stringify(invoked.arguments),
                "status.ok": observed.ok,
        }
        if observed.error is not None:
                attributes["exception.message"] = observed.error
        return SpanData(name=f"tool {invoked.tool_name}", attributes=attributes)


def _stringify(arguments: Mapping[str, object]) -> str:
        return ", ".join(f"{key}={value!r}" for key, value in arguments.items())
