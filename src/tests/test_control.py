"""Tests for the control subsystem: decisions, guards, and the controller."""

import pytest

from harness.control import Controller, Decision, Guard, IterationLimiter, ProgressTracker
from harness.runtime import AgentExecutionContext
from harness.tools import ToolResult
from llm import Completion, Conversation, Message, ToolCall


def _context_after(iterations: int) -> AgentExecutionContext:
        context = AgentExecutionContext.for_task("t-1", Conversation.of([Message.user("go")]))
        for _ in range(iterations):
                context = context.with_assistant(Completion())  # each model turn bumps the counter
        return context


def test_decision_factories():
        assert Decision.allow().allowed
        assert not Decision.allow().denied()
        denied = Decision.deny("nope")
        assert denied.denied()
        assert denied.reason == "nope"


def test_iteration_limiter_allows_below_the_cap():
        limiter = IterationLimiter(max_iterations=3)
        assert not limiter.evaluate(_context_after(2)).denied()


def test_iteration_limiter_denies_at_and_above_the_cap():
        limiter = IterationLimiter(max_iterations=3)
        decision = limiter.evaluate(_context_after(3))
        assert decision.denied()
        assert "iteration cap" in decision.reason


def test_iteration_limiter_rejects_nonpositive_cap():
        with pytest.raises(ValueError, match="at least 1"):
                IterationLimiter(max_iterations=0)


def test_iteration_limiter_conforms_to_guard_port():
        guard: Guard = IterationLimiter(max_iterations=1)
        assert isinstance(guard, Guard)


def test_empty_controller_permits():
        assert Controller().permit(_context_after(99)).allowed


def test_controller_returns_first_denial_in_order():
        class AlwaysDeny:
                @property
                def name(self) -> str:
                        return "always-deny"

                def evaluate(self, context: AgentExecutionContext) -> Decision:
                        return Decision.deny("blocked")

        controller = Controller([IterationLimiter(max_iterations=10), AlwaysDeny()])
        decision = controller.permit(_context_after(0))
        assert decision.denied()
        assert decision.reason == "blocked"


# --- ProgressTracker (no-progress loop detection) ---------------------------


def _looped(times: int, *, vary: bool = False) -> AgentExecutionContext:
        """A context whose last ``times`` cycles each called the same tool.

        With ``vary`` the arguments/result differ per cycle, so the signatures
        diverge (genuine progress); otherwise every cycle is identical.
        """
        context = AgentExecutionContext.for_task("t-1", Conversation.of([Message.user("go")]))
        for index in range(times):
                token = str(index) if vary else "x"
                call = ToolCall(id=f"c{index}", name="search", arguments={"q": token})
                result = ToolResult.success(call_id=f"c{index}", tool_name="search", content=token)
                acted = context.with_assistant(Completion(tool_calls=(call,))).with_tool_results([result])
                context = acted.observed()
        return context


def test_tracker_reports_advancing_with_no_history():
        assert ProgressTracker().assess(_looped(0)).advancing()


def test_tracker_reports_advancing_while_signatures_differ():
        assert ProgressTracker().assess(_looped(5, vary=True)).advancing()


def test_tracker_stalls_on_the_first_repeat_then_stops_on_a_further_one():
        tracker = ProgressTracker()

        stalling = tracker.assess(_looped(2))
        assert stalling.stalling()
        assert not stalling.stalled()

        stalled = tracker.assess(_looped(3))
        assert stalled.stalled()
        assert not stalled.stalling()


def test_tracker_reason_explains_the_repetition():
        assessment = ProgressTracker().assess(_looped(3))
        assert "repeat" in assessment.reason.lower()


def test_tracker_rejects_incoherent_thresholds():
        with pytest.raises(ValueError, match="stall_at"):
                ProgressTracker(stall_at=1)
        with pytest.raises(ValueError, match="stop_at"):
                ProgressTracker(stall_at=3, stop_at=3)
