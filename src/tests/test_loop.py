"""Behavioral tests for the loop: a full ReAct cycle and a controlled abort.

Driven entirely by a scripted ``FakeChatModel`` and the ``EchoTool`` -- no real
model or network.
"""

from harness.assembly import build_agent_loop
from harness.control import Controller, IterationLimiter
from harness.events import (
        AuditLogger,
        CycleCompleted,
        EventBus,
        GuardTripped,
        LoopStopped,
        ModelCalled,
        ModelCompleted,
        StrategyNudged,
        ToolInvoked,
        ToolObserved,
)
from harness.loop import (
        ActionPhase,
        AgentLoop,
        Continue,
        Halt,
        Navigator,
        ObservationPhase,
        Outcome,
        ReasonPhase,
)
from harness.runtime import AgentExecutionContext, ExecutionState
from harness.tools import ToolExecutor, ToolRegistry
from harness.tools.adapters import EchoTool
from llm import Completion, Conversation, Message, Role, ToolCall
from tests.doubles import FakeChatModel


def _context(task: str = "echo hi") -> AgentExecutionContext:
        return AgentExecutionContext.for_task("t-1", Conversation.of([Message.user(task)]))


def _wire(
        model: FakeChatModel, *, max_iterations: int = 5
) -> tuple[AgentLoop, AuditLogger, ReasonPhase]:
        bus = EventBus()
        audit = AuditLogger()
        bus.subscribe(audit)

        registry = ToolRegistry()
        registry.register(EchoTool())
        executor = ToolExecutor(registry, bus)

        reason = ReasonPhase(model, registry.catalog(), bus)
        action = ActionPhase(executor)
        observation = ObservationPhase(
                Controller([IterationLimiter(max_iterations=max_iterations)]), bus
        )
        navigator = Navigator(
                start=reason,
                transitions={
                        (reason, Outcome.TOOLS_REQUESTED): Continue(action),
                        (reason, Outcome.ANSWERED): Halt(),
                        (action, Outcome.ACTED): Continue(observation),
                        (observation, Outcome.CONTINUE): Continue(reason),
                        (observation, Outcome.DENIED): Halt(),
                },
        )
        return AgentLoop(navigator, bus), audit, reason


async def test_full_react_cycle_runs_tool_then_answers():
        model = FakeChatModel(
                [
                        Completion(tool_calls=(ToolCall(id="c1", name="echo", arguments={"text": "hi"}),)),
                        Completion(content="I echoed: hi"),
                ]
        )
        loop, audit, _ = _wire(model)

        result = await loop.run(_context())

        assert result.succeeded()
        assert result.state is ExecutionState.COMPLETED
        assert result.final_output == "I echoed: hi"
        assert result.metadata.iterations == 2  # model called twice: request tool, then answer

        kinds = [type(e) for e in audit.records()]
        assert ModelCalled in kinds
        assert ToolInvoked in kinds
        assert ToolObserved in kinds
        assert CycleCompleted in kinds
        assert kinds[-1] is LoopStopped


async def test_model_completed_event_carries_model_tokens_latency_and_cost():
        model = FakeChatModel([Completion(content="done")])
        loop, audit, _ = _wire(model)

        await loop.run(_context())

        completed = [e for e in audit.records() if isinstance(e, ModelCompleted)]
        assert len(completed) == 1
        event = completed[0]
        assert event.model == "fake-model"
        assert event.output == "done"
        assert event.latency_ms >= 0.0
        assert event.cost_usd == 0.0  # fake-model is not in the price table

        called = [e for e in audit.records() if isinstance(e, ModelCalled)]
        assert called[0].model == "fake-model"


async def test_failing_tool_reports_the_error_on_the_observation_event():
        model = FakeChatModel(
                [
                        Completion(tool_calls=(ToolCall(id="c1", name="ghost", arguments={}),)),
                        Completion(content="handled"),
                ]
        )
        loop, audit, _ = _wire(model)

        await loop.run(_context())

        observed = [e for e in audit.records() if isinstance(e, ToolObserved)]
        assert observed[0].ok is False
        assert observed[0].error is not None
        assert "ghost" in observed[0].error


async def test_answer_without_tools_stops_immediately():
        model = FakeChatModel([Completion(content="done, no tools needed")])
        loop, _, _ = _wire(model)

        result = await loop.run(_context("just answer"))

        assert result.succeeded()
        assert result.final_output == "done, no tools needed"
        assert result.metadata.iterations == 1  # a single model call still counts as one pass


async def test_observation_message_is_folded_into_the_conversation():
        model = FakeChatModel(
                [
                        Completion(tool_calls=(ToolCall(id="c1", name="echo", arguments={"text": "pong"}),)),
                        Completion(content="ok"),
                ]
        )
        loop, _, _ = _wire(model)
        await loop.run(_context())

        second_call_conversation = model.calls[1][0]
        tool_messages = [m for m in second_call_conversation if m.role is Role.TOOL]
        assert [m.content for m in tool_messages] == ["pong"]


async def test_iteration_cap_aborts_a_non_converging_run():
        looping = [
                Completion(tool_calls=(ToolCall(id=f"c{i}", name="echo", arguments={"text": "x"}),))
                for i in range(10)
        ]
        model = FakeChatModel(looping)
        loop, _, _ = _wire(model, max_iterations=2)

        result = await loop.run(_context())

        assert not result.succeeded()
        assert result.state is ExecutionState.ABORTED
        assert result.metadata.iterations == 2
        assert "iteration cap" in (result.stop_reason or "")


async def test_progress_tracker_nudges_then_stops_a_repeating_model():
        # The model keeps asking for the same call with the same arguments; the
        # tracker (default-on in the real assembly) should intervene well before
        # the far-off iteration cap.
        repeat = Completion(tool_calls=(ToolCall(id="c1", name="echo", arguments={"text": "loop"}),))
        model = FakeChatModel([repeat, repeat, repeat])

        bus = EventBus()
        audit = AuditLogger()
        bus.subscribe(audit)
        registry = ToolRegistry()
        registry.register(EchoTool())
        loop = build_agent_loop(
                model=model,
                registry=registry,
                controller=Controller([IterationLimiter(max_iterations=20)]),
                event_bus=bus,
        )

        result = await loop.run(_context())

        assert result.state is ExecutionState.ABORTED
        assert "progress-tracker" in (result.stop_reason or "")
        assert result.metadata.iterations < 20  # stopped for stalling, not the hard cap

        kinds = [type(e) for e in audit.records()]
        assert StrategyNudged in kinds  # nudged on the first repeat
        assert GuardTripped in kinds  # then stopped on the next

        # The corrective guidance was folded into the conversation as feedback.
        nudges = [
                m
                for m in result.conversation.messages()
                if m.role is Role.USER and "repeated the same action" in m.content
        ]
        assert len(nudges) == 1


async def test_step_runs_a_single_phase_and_reports_its_outcome():
        model = FakeChatModel(
                [Completion(tool_calls=(ToolCall(id="c1", name="echo", arguments={"text": "hi"}),))]
        )
        loop, _, reason = _wire(model)

        result = await loop.step(_context(), reason)

        assert result.outcome is Outcome.TOOLS_REQUESTED
        assert result.context.has_pending_actions()
