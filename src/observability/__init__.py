"""Observability: turn the harness event stream into external traces.

Only the pure span mapping is exported here. The Phoenix/OpenTelemetry boundary
lives in ``observability.phoenix`` and is imported directly by the composition
root when enabled, so importing this package never requires Phoenix installed.
"""

from observability.spans import SpanData, llm_span, tool_span

__all__ = [
        "SpanData",
        "llm_span",
        "tool_span",
]
