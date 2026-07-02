"""Integration tests for concrete subagents and principal delegation."""

from __future__ import annotations

from agent.subagent import Subagent
from harness.assembly import build_agent_loop
from harness.control import Controller, IterationLimiter
from harness.delegation import SubagentRegistry
from harness.events import EventBus
from harness.runtime import AgentExecutionContext
from harness.tools import ToolRegistry
from harness.tools.adapters import EchoTool
from llm import Completion, Conversation, Message, ToolCall
from tests.doubles import FakeChatModel


async def test_subagent_runs_its_inner_loop_and_reports_its_answer() -> None:
        model = FakeChatModel([Completion(content="the repo uses APIRouter")])
        explorer = Subagent(
                name="explore",
                description="maps the repo",
                system_prompt="You are the Explorer.",
                model=model,
        )

        report = await explorer.delegate("describe the architecture")

        assert report.agent == "explore"
        assert report.succeeded is True
        assert report.output == "the repo uses APIRouter"


async def test_principal_delegates_then_synthesizes_and_merges_the_ledger() -> None:
        subagent_model = FakeChatModel([Completion(content="found: FastAPI + pytest")])
        explorer = Subagent(
                name="explore",
                description="maps the repo",
                system_prompt="You are the Explorer.",
                model=subagent_model,
        )

        # Principal: first turn delegates to explore, second turn answers.
        principal_model = FakeChatModel(
                [
                        Completion(
                                tool_calls=(
                                        ToolCall(id="c1", name="explore", arguments={"task": "map it"}),
                                )
                        ),
                        Completion(content="Report: the project is FastAPI + pytest."),
                ]
        )

        registry = ToolRegistry()
        registry.register(EchoTool())
        loop = build_agent_loop(
                model=principal_model,
                registry=registry,
                controller=Controller([IterationLimiter(5)]),
                event_bus=EventBus(),
                subagents=SubagentRegistry([explorer]),
        )

        context = AgentExecutionContext.for_task(
                "t-1",
                Conversation.of([Message.user("analyze the repo")]),
                request="analyze the repo",
        )
        result = await loop.run(context)

        assert result.succeeded()
        assert result.final_output == "Report: the project is FastAPI + pytest."
        # The subagent's work was merged into the principal's shared ledger.
        assert [r.agent for r in result.ledger.subagent_results()] == ["explore"]
        assert result.ledger.subagent_results()[0].summary == "found: FastAPI + pytest"
        assert result.ledger.original_request() == "analyze the repo"


async def test_capped_subagent_returns_partial_findings_not_just_the_halt_reason() -> None:
        # A subagent capped before answering should still hand back what it found
        # (via a forced synthesis turn), plus why the report is partial.
        model = FakeChatModel(
                [
                        Completion(tool_calls=(ToolCall(id="c1", name="echo", arguments={"text": "x"}),)),
                        Completion(content="I ran echo once but could not finish the checks."),
                ]
        )
        tester = Subagent(
                name="test",
                description="runs checks",
                system_prompt="You are the Tester.",
                model=model,
                tools=[EchoTool()],
                max_iterations=1,
        )

        report = await tester.delegate("run the suite")

        assert report.succeeded is False
        assert "could not finish the checks" in report.output  # synthesized findings
        assert "iteration cap" in report.output  # and why it is partial
