"""The Phoenix/OpenTelemetry boundary (outer ring, untested by design).

``PhoenixTracer`` is an ``EventHandler`` that turns the harness event stream
into nested OpenTelemetry spans: a run root, an LLM span per model call, and a
tool span per tool call. It pairs start/end events (``ModelCalled`` with
``ModelCompleted``; ``ToolInvoked`` with ``ToolObserved`` by ``call_id``) so the
spans carry real durations. The attribute mapping lives in the pure
``observability.spans`` module; only the OTel I/O lives here.

Importing this module requires OpenTelemetry (installed via the ``observability``
extra); the composition root imports it only when observability is enabled.
"""

# pyright: reportMissingImports=false

from __future__ import annotations

from datetime import datetime
from typing import cast

from opentelemetry.context import Context
from opentelemetry.trace import Span, Tracer, set_span_in_context
from opentelemetry.util.types import AttributeValue

from harness.events import (
        Event,
        LoopStopped,
        ModelCalled,
        ModelCompleted,
        ToolInvoked,
        ToolObserved,
)
from observability.spans import SPAN_KIND, SpanData, llm_span, tool_span


def _nanos(moment: datetime) -> int:
        return int(moment.timestamp() * 1_000_000_000)


class PhoenixTracer:
        """Maps the event stream onto OpenTelemetry spans for Phoenix."""

        def __init__(self, tracer: Tracer) -> None:
                self._tracer = tracer
                self._root: Span | None = None
                self._root_ctx: Context | None = None
                self._pending_call: ModelCalled | None = None
                self._llm_span: Span | None = None
                self._tools: dict[str, tuple[ToolInvoked, Span]] = {}

        def handle(self, event: Event) -> None:
                self._ensure_root(event)
                match event:
                        case ModelCalled():
                                self._pending_call = event
                                self._llm_span = self._tracer.start_span(
                                        f"llm {event.model}",
                                        context=self._root_ctx,
                                        start_time=_nanos(event.occurred_at),
                                )
                        case ModelCompleted():
                                self._close_llm_span(event)
                        case ToolInvoked():
                                self._tools[event.call_id] = (
                                        event,
                                        self._tracer.start_span(
                                                f"tool {event.tool_name}",
                                                context=self._root_ctx,
                                                start_time=_nanos(event.occurred_at),
                                        ),
                                )
                        case ToolObserved():
                                self._close_tool_span(event)
                        case LoopStopped() if event.source == "":
                                # Only the principal's stop ends the run root; a
                                # subagent's stop (forwarded, source-tagged) must not,
                                # or its activity would fall outside the run tree.
                                self._close_root(event)
                        case _:
                                pass

        def _ensure_root(self, event: Event) -> None:
                if self._root is not None:
                        return
                root = self._tracer.start_span(
                        "agent.run", start_time=_nanos(event.occurred_at)
                )
                root.set_attribute(SPAN_KIND, "CHAIN")
                root.set_attribute("agent.name", "principal")
                self._root = root
                self._root_ctx = set_span_in_context(root)

        def _close_llm_span(self, event: ModelCompleted) -> None:
                if self._pending_call is None or self._llm_span is None:
                        return
                _apply(self._llm_span, llm_span(self._pending_call, event))
                self._llm_span.end(end_time=_nanos(event.occurred_at))
                self._pending_call = None
                self._llm_span = None

        def _close_tool_span(self, event: ToolObserved) -> None:
                pair = self._tools.pop(event.call_id, None)
                if pair is None:
                        return
                invoked, span = pair
                _apply(span, tool_span(invoked, event))
                span.end(end_time=_nanos(event.occurred_at))

        def _close_root(self, event: LoopStopped) -> None:
                if self._root is None:
                        return
                self._root.set_attribute("output.value", event.output or "")
                self._root.end(end_time=_nanos(event.occurred_at))
                self._root = None
                self._root_ctx = None


def _apply(span: Span, data: SpanData) -> None:
        for key, value in data.attributes.items():
                span.set_attribute(key, cast(AttributeValue, value))


def launch_phoenix_tracer(project_name: str = "advanced-agent") -> PhoenixTracer:
        """Launch a local Phoenix UI and return a tracer wired to it.

        Lazy-imports Phoenix so the rest of the package never needs it.
        """
        import phoenix as px
        from phoenix.otel import register

        px.launch_app()
        provider = register(project_name=project_name)
        return PhoenixTracer(cast(Tracer, provider.get_tracer(project_name)))
