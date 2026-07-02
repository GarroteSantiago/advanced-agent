"""Tests for the DelegatingActionPhase: routing + ledger merge."""

from __future__ import annotations

from collections.abc import Mapping

from harness.delegation import SubagentRegistry, SubagentReport
from harness.loop import DelegatingActionPhase, Outcome
from harness.runtime import AgentExecutionContext, Source
from harness.tools import ToolExecutor, ToolRegistry
from harness.tools.adapters import EchoTool
from llm import Completion, Conversation, Message, ToolCall


class FakeDelegate:
        def __init__(self, name: str, report: SubagentReport) -> None:
                self._name = name
                self._report = report
                self.received: str | None = None

        @property
        def name(self) -> str:
                return self._name

        @property
        def description(self) -> str:
                return "fake"

        def parameters(self) -> Mapping[str, object]:
                return {"type": "object", "properties": {"task": {"type": "string"}}}

        async def delegate(self, task: str) -> SubagentReport:
                self.received = task
                return self._report


def _context_with_calls(*calls: ToolCall) -> AgentExecutionContext:
        base = AgentExecutionContext.for_task(
                "t-1", Conversation.of([Message.user("go")]), request="go"
        )
        return base.with_assistant(Completion(tool_calls=calls))


def _phase(*subagents: FakeDelegate) -> DelegatingActionPhase:
        registry = ToolRegistry()
        registry.register(EchoTool())
        return DelegatingActionPhase(ToolExecutor(registry), SubagentRegistry(subagents))


async def test_delegation_merges_the_report_into_the_shared_ledger() -> None:
        report = SubagentReport(
                agent="explore",
                output="mapped the tree",
                sources=(Source.from_repo("src/app.py"),),
                modified_files=("notes.md",),
                observations=("uses APIRouter",),
        )
        explorer = FakeDelegate("explore", report)
        phase = _phase(explorer)
        context = _context_with_calls(ToolCall(id="c1", name="explore", arguments={"task": "map it"}))

        result = await phase.run(context)

        assert result.outcome is Outcome.ACTED
        assert explorer.received == "map it"
        ledger = result.context.ledger()
        assert [r.agent for r in ledger.subagent_results()] == ["explore"]
        assert ledger.subagent_results()[0].succeeded is True
        assert [s.reference for s in ledger.sources_consulted()] == ["src/app.py"]
        assert ledger.modified_files() == ("notes.md",)
        assert ledger.observations() == ("uses APIRouter",)


async def test_ordinary_tool_calls_still_run_through_the_executor() -> None:
        phase = _phase(FakeDelegate("explore", SubagentReport.completed("explore", "x")))
        context = _context_with_calls(
                ToolCall(id="c1", name="echo", arguments={"text": "hi"}),
        )

        result = await phase.run(context)

        # echo ran; no subagent was credited.
        assert result.context.ledger().subagent_results() == ()
        last = result.context.current_conversation()  # unchanged until observed()
        assert last is not None


async def test_failed_delegation_is_reported_as_a_failed_tool_result() -> None:
        phase = _phase(FakeDelegate("test", SubagentReport.failed("test", "build broke")))
        context = _context_with_calls(ToolCall(id="c1", name="test", arguments={"task": "run"}))

        result = await phase.run(context)

        ledger = result.context.ledger()
        assert ledger.subagent_results()[0].succeeded is False
        assert ledger.subagent_results()[0].summary == "build broke"
