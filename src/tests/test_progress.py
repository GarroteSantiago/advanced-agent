"""Tests for the live ProgressView event handler."""

from agent.progress import ProgressView, _summarize
from harness.events import (
        GuardTripped,
        ModelCalled,
        PhaseStarted,
        StrategyNudged,
        ToolInvoked,
        ToolObserved,
)
from tests.doubles import FakeRenderer


def test_shows_model_tool_and_guard_activity():
        renderer = FakeRenderer()
        view = ProgressView(renderer)

        view.handle(ModelCalled(message_count=2, offered_tools=1))
        view.handle(ToolInvoked(tool_name="read_file", call_id="c1", arguments={"path": "x.py"}))
        view.handle(ToolObserved(tool_name="read_file", call_id="c1", ok=True))
        view.handle(GuardTripped(guard="controller", reason="iteration cap reached"))

        text = "\n".join(renderer.lines)
        assert "thinking" in text
        assert "→ read_file(path=x.py)" in text
        assert "✓ read_file" in text
        assert "iteration cap reached" in text


def test_shows_a_strategy_nudge_always():
        renderer = FakeRenderer()
        ProgressView(renderer, verbose=False).handle(
                StrategyNudged(reason="repeated 2 times", occurrences=2)
        )
        assert any("nudging" in line for line in renderer.lines)


def test_failed_tool_shows_a_cross():
        renderer = FakeRenderer()
        ProgressView(renderer).handle(ToolObserved(tool_name="write_file", call_id="c1", ok=False))
        assert any("✗ write_file" in line for line in renderer.lines)


def test_phase_events_are_hidden_unless_verbose():
        quiet = FakeRenderer()
        ProgressView(quiet, verbose=False).handle(PhaseStarted(phase="reason"))
        assert quiet.lines == []

        loud = FakeRenderer()
        ProgressView(loud, verbose=True).handle(PhaseStarted(phase="reason"))
        assert any("reason" in line for line in loud.lines)


def test_summarize_clips_long_argument_values():
        summary = _summarize({"content": "x" * 100})
        assert summary.startswith("content=")
        assert "…" in summary
        assert len(summary) < 60


def test_summarize_flattens_newlines_and_joins_multiple_args():
        summary = _summarize({"path": "a.txt", "content": "line1\nline2"})
        assert "\n" not in summary
        assert "path=a.txt" in summary
        assert "content=line1 line2" in summary
