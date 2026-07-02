"""Tests for the pure event->span mapping (no Phoenix required)."""

from __future__ import annotations

from harness.events import ModelCalled, ModelCompleted, ToolInvoked, ToolObserved
from observability.spans import SPAN_KIND, llm_span, tool_span


def test_llm_span_carries_model_tokens_latency_and_cost() -> None:
        called = ModelCalled(message_count=3, offered_tools=2, model="gpt-5-nano")
        completed = ModelCompleted(
                model="gpt-5-nano",
                prompt_tokens=10,
                completion_tokens=5,
                latency_ms=42.0,
                cost_usd=0.001,
                output="the answer",
        )

        span = llm_span(called, completed)

        assert span.attributes[SPAN_KIND] == "LLM"
        assert span.attributes["llm.model_name"] == "gpt-5-nano"
        assert span.attributes["llm.token_count.prompt"] == 10
        assert span.attributes["llm.token_count.completion"] == 5
        assert span.attributes["llm.token_count.total"] == 15
        assert span.attributes["llm.latency_ms"] == 42.0
        assert span.attributes["llm.cost.total_usd"] == 0.001
        assert span.attributes["output.value"] == "the answer"
        assert span.attributes["agent.name"] == "principal"  # empty source == principal


def test_spans_attribute_forwarded_events_to_their_subagent() -> None:
        called = ModelCalled(message_count=1, offered_tools=0, model="gpt-5-nano", source="research")
        completed = ModelCompleted(
                model="gpt-5-nano",
                prompt_tokens=1,
                completion_tokens=1,
                latency_ms=1.0,
                cost_usd=0.0,
                source="research",
        )
        invoked = ToolInvoked(tool_name="rag_search", call_id="c1", arguments={}, source="research")
        observed = ToolObserved(tool_name="rag_search", call_id="c1", ok=True, source="research")

        assert llm_span(called, completed).attributes["agent.name"] == "research"
        assert tool_span(invoked, observed).attributes["agent.name"] == "research"


def test_tool_span_records_name_input_and_success() -> None:
        invoked = ToolInvoked(tool_name="read_file", call_id="c1", arguments={"path": "a.py"})
        observed = ToolObserved(tool_name="read_file", call_id="c1", ok=True)

        span = tool_span(invoked, observed)

        assert span.attributes[SPAN_KIND] == "TOOL"
        assert span.attributes["tool.name"] == "read_file"
        assert span.attributes["status.ok"] is True
        assert "path=" in str(span.attributes["input.value"])
        assert "exception.message" not in span.attributes


def test_tool_span_records_the_error_when_the_tool_fails() -> None:
        invoked = ToolInvoked(tool_name="ghost", call_id="c9", arguments={})
        observed = ToolObserved(tool_name="ghost", call_id="c9", ok=False, error="no tool named 'ghost'")

        span = tool_span(invoked, observed)

        assert span.attributes["status.ok"] is False
        assert span.attributes["exception.message"] == "no tool named 'ghost'"
