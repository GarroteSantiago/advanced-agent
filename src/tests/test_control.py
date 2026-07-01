"""Tests for the control subsystem: decisions, guards, and the controller."""

import pytest

from harness.control import Controller, Decision, Guard, IterationLimiter
from harness.runtime import AgentExecutionContext
from llm import Completion, Conversation, Message


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
