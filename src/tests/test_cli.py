"""Tests for the CLI: console adapters and the REPL, all driven through ports."""

from agent import ApprovePlan, RejectPlan, RevisePlan
from agent.cli import ConsoleConfirmer, ConsoleReviewer, build_session, run_chat
from harness.tools import ToolRequest
from llm import Completion
from tests.doubles import FakeChatModel, FakeInputer, FakeRenderer


def _request() -> ToolRequest:
        return ToolRequest(call_id="c1", tool_name="write_file", arguments={"path": "x"})


async def test_confirmer_accepts_yes():
        assert await ConsoleConfirmer(FakeInputer("y")).confirm(_request())


async def test_confirmer_defaults_to_no():
        assert not await ConsoleConfirmer(FakeInputer("")).confirm(_request())


async def test_confirmer_treats_eof_as_decline():
        assert not await ConsoleConfirmer(FakeInputer()).confirm(_request())


async def test_reviewer_approve():
        reviewer = ConsoleReviewer(FakeRenderer(), FakeInputer("a"))
        assert isinstance(await reviewer.review("the plan"), ApprovePlan)


async def test_reviewer_reject():
        reviewer = ConsoleReviewer(FakeRenderer(), FakeInputer("r"))
        assert isinstance(await reviewer.review("the plan"), RejectPlan)


async def test_reviewer_revise_collects_feedback():
        reviewer = ConsoleReviewer(FakeRenderer(), FakeInputer("v", "do it differently"))
        review = await reviewer.review("the plan")
        assert isinstance(review, RevisePlan)
        assert review.feedback == "do it differently"


def test_build_session_wires_modes_off_by_default():
        session, supervision, plan_mode, progress = build_session(
                FakeChatModel([]), renderer=FakeRenderer(), inputer=FakeInputer()
        )
        assert session is not None
        assert supervision.enabled is False
        assert plan_mode.enabled is False
        assert progress.verbose is False


async def test_run_chat_renders_reply_and_live_progress():
        renderer = FakeRenderer()
        inputer = FakeInputer("hello")  # one message, then EOF ends the loop
        session, supervision, plan_mode, progress = build_session(
                FakeChatModel([Completion(content="hi from agent")]),
                renderer=renderer,
                inputer=inputer,
        )

        await run_chat(
                session,
                supervision=supervision,
                plan_mode=plan_mode,
                progress=progress,
                renderer=renderer,
                inputer=inputer,
        )

        assert any("hi from agent" in line for line in renderer.lines)
        assert any("thinking" in line for line in renderer.lines)  # progress rendered live


async def test_run_chat_toggles_all_modes_without_calling_the_model():
        renderer = FakeRenderer()
        inputer = FakeInputer("/plan", "/supervise", "/verbose")  # then EOF
        session, supervision, plan_mode, progress = build_session(
                FakeChatModel([]), renderer=renderer, inputer=inputer
        )

        await run_chat(
                session,
                supervision=supervision,
                plan_mode=plan_mode,
                progress=progress,
                renderer=renderer,
                inputer=inputer,
        )

        assert plan_mode.enabled is True
        assert supervision.enabled is True
        assert progress.verbose is True
        assert any("plan mode on" in line for line in renderer.lines)
