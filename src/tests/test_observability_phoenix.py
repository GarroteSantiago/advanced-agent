"""Smoke test for the Phoenix/OpenTelemetry boundary against a real OTel SDK.

Unlike ``test_observability_spans`` (which tests the pure mapping with no
dependency), this drives ``PhoenixTracer`` with a genuine in-memory OTel tracer
and asserts the emitted spans -- names, attributes, and parent/child nesting.
It needs the ``observability`` extra, so it is skipped when OTel is absent (the
default ``just validate`` environment); run ``uv sync --extra observability``
to exercise it.
"""

# pyright: reportMissingImports=false

from __future__ import annotations

import pytest

pytest.importorskip("opentelemetry.sdk")

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
)

from harness.events import (
        LoopStopped,
        ModelCalled,
        ModelCompleted,
        ToolInvoked,
        ToolObserved,
)
from observability.phoenix import PhoenixTracer


def _tracer() -> tuple[PhoenixTracer, InMemorySpanExporter]:
        exporter = InMemorySpanExporter()
        provider = TracerProvider()
        provider.add_span_processor(SimpleSpanProcessor(exporter))
        return PhoenixTracer(provider.get_tracer("test")), exporter


def test_boundary_emits_nested_llm_and_tool_spans_with_attributes() -> None:
        tracer, exporter = _tracer()

        tracer.handle(ModelCalled(message_count=3, offered_tools=2, model="gpt-5-nano"))
        tracer.handle(
                ModelCompleted(
                        model="gpt-5-nano",
                        prompt_tokens=10,
                        completion_tokens=5,
                        latency_ms=12.0,
                        cost_usd=0.001,
                        output="hi",
                )
        )
        tracer.handle(
                ToolInvoked(
                        tool_name="rag_search", call_id="c1", arguments={"q": "routing"}, source="research"
                )
        )
        tracer.handle(ToolObserved(tool_name="rag_search", call_id="c1", ok=True, source="research"))
        tracer.handle(LoopStopped(reason="done", output="final report"))

        spans = {s.name: s for s in exporter.get_finished_spans()}
        assert set(spans) == {"agent.run", "llm gpt-5-nano", "tool rag_search"}

        llm, tool, root = spans["llm gpt-5-nano"], spans["tool rag_search"], spans["agent.run"]
        # Narrow OTel's Optional span fields.
        assert llm.attributes is not None
        assert tool.attributes is not None
        assert root.attributes is not None
        assert root.context is not None
        assert llm.parent is not None
        assert tool.parent is not None

        assert llm.attributes["llm.token_count.total"] == 15
        assert llm.attributes["agent.name"] == "principal"
        assert tool.attributes["tool.name"] == "rag_search"
        assert tool.attributes["agent.name"] == "research"  # forwarded-event provenance
        assert root.attributes["output.value"] == "final report"

        # Both the model and tool spans nest under the single run root.
        assert llm.parent.span_id == root.context.span_id
        assert tool.parent.span_id == root.context.span_id


def test_a_subagent_stop_does_not_close_the_principal_run_root() -> None:
        # Subagent stops are forwarded source-tagged; only the principal's
        # (source="") stop may close the run root, else its spans would
        # escape the tree and a second root would open for later work.
        tracer, exporter = _tracer()
        tracer.handle(ModelCalled(message_count=1, offered_tools=1, model="gpt-5-nano"))
        tracer.handle(
                ModelCompleted(
                        model="gpt-5-nano",
                        prompt_tokens=1,
                        completion_tokens=1,
                        latency_ms=1.0,
                        cost_usd=0.0,
                )
        )
        tracer.handle(LoopStopped(reason="subagent done", output="partial", source="explore"))
        assert not [s for s in exporter.get_finished_spans() if s.name == "agent.run"]

        tracer.handle(LoopStopped(reason="done", output="final"))
        roots = [s for s in exporter.get_finished_spans() if s.name == "agent.run"]
        assert len(roots) == 1
