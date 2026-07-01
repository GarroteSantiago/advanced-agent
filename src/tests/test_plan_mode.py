"""Tests for plan mode: plan -> approve/reject/revise before acting."""

from agent import ApprovePlan, PlanMode, PlanReview, RejectPlan, RevisePlan, Session
from llm import Completion, Role
from tests.doubles import FakeChatModel


class _ScriptedReviewer:
        def __init__(self, *reviews: PlanReview) -> None:
                self._reviews = list(reviews)
                self.seen: list[str] = []

        async def review(self, plan: str) -> PlanReview:
                self.seen.append(plan)
                return self._reviews.pop(0)


async def test_plan_mode_disabled_acts_directly():
        model = FakeChatModel([Completion(content="answer")])
        session = Session(model, plan_mode=PlanMode(_ScriptedReviewer(), enabled=False))

        result = await session.ask("do it")

        assert result.succeeded()
        assert len(model.calls) == 1  # no planning call


async def test_approved_plan_runs_the_task():
        model = FakeChatModel(
                [Completion(content="1. do x\n2. do y"), Completion(content="done")]
        )
        reviewer = _ScriptedReviewer(ApprovePlan())
        session = Session(model, plan_mode=PlanMode(reviewer, enabled=True))

        result = await session.ask("do it")

        assert result.succeeded()
        assert result.final_output == "done"
        assert reviewer.seen == ["1. do x\n2. do y"]
        assert any(m.role is Role.ASSISTANT and "do x" in m.content for m in result.conversation)


async def test_rejected_plan_executes_nothing():
        model = FakeChatModel([Completion(content="the plan")])  # only the planning call
        session = Session(model, plan_mode=PlanMode(_ScriptedReviewer(RejectPlan()), enabled=True))

        result = await session.ask("do it")

        assert not result.succeeded()
        assert "rejected" in (result.stop_reason or "")
        assert len(model.calls) == 1  # action loop never ran


async def test_revised_then_approved_replans():
        model = FakeChatModel(
                [
                        Completion(content="plan v1"),
                        Completion(content="plan v2"),
                        Completion(content="done"),
                ]
        )
        reviewer = _ScriptedReviewer(RevisePlan("also add tests"), ApprovePlan())
        session = Session(model, plan_mode=PlanMode(reviewer, enabled=True))

        result = await session.ask("do it")

        assert result.succeeded()
        assert reviewer.seen == ["plan v1", "plan v2"]
        assert len(model.calls) == 3  # plan v1, plan v2, then the action turn
        assert any(m.role is Role.USER and "add tests" in m.content for m in result.conversation)
