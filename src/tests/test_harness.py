"""Integration test for the Harness composition root.

A scripted model requests a tool, then answers; we assert the full
reason -> act -> observe -> reason cycle ran and the audit stream recorded it.
"""

from harness import Harness
from harness.events import (
        AuditLogger,
        CycleCompleted,
        LoopStopped,
        ModelCalled,
        PhaseStarted,
        ToolInvoked,
        ToolObserved,
)
from harness.tools.adapters import EchoTool
from llm import Completion, ToolCall
from tests.doubles import FakeChatModel


async def test_harness_runs_a_full_react_cycle_and_records_a_trace():
        model = FakeChatModel(
                [
                        Completion(
                                content="let me check",
                                tool_calls=(ToolCall(id="c1", name="echo", arguments={"text": "pong"}),),
                        ),
                        Completion(content="the tool said pong"),
                ]
        )
        audit = AuditLogger()
        harness = Harness(model, tools=[EchoTool()], handlers=[audit], max_iterations=5)

        result = await harness.run("ping the echo tool")

        assert result.succeeded()
        assert result.final_output == "the tool said pong"
        assert result.metadata.iterations == 2  # request tool, then answer

        # A complete trace: phases bracketed, model+tool calls, cycle closed, stop.
        kinds = [type(e) for e in audit.records()]
        assert kinds[0] is PhaseStarted
        for expected in (ModelCalled, ToolInvoked, ToolObserved, CycleCompleted):
                assert expected in kinds
        assert kinds[-1] is LoopStopped


async def test_harness_answers_directly_when_no_tools_are_needed():
        model = FakeChatModel([Completion(content="42")])
        harness = Harness(model)

        result = await harness.run("what is six times seven?")

        assert result.succeeded()
        assert result.final_output == "42"
        assert result.metadata.iterations == 1


async def test_observers_can_subscribe_through_the_events_property():
        model = FakeChatModel([Completion(content="hi")])
        harness = Harness(model)
        late = AuditLogger()
        harness.events.subscribe(late)

        await harness.run("say hi")

        assert any(isinstance(e, LoopStopped) for e in late.records())
