"""Tests for the runtime spine: metadata, context transitions, and result."""

from harness.runtime import (
        AgentExecutionContext,
        ExecutionMetadata,
        ExecutionResult,
        ExecutionState,
)
from harness.tools import ToolResult
from llm import Completion, Conversation, Message, Role, TokenUsage, ToolCall


def _started() -> AgentExecutionContext:
        convo = Conversation.of([Message.user("do the thing")])
        return AgentExecutionContext.for_task("t-1", convo)


def test_metadata_increments_and_accumulates_usage_without_mutation():
        base = ExecutionMetadata(task_id="t-1")
        advanced = base.incremented().add_usage(TokenUsage(prompt_tokens=3, completion_tokens=2))

        assert base.iterations == 0  # original untouched
        assert advanced.iterations == 1
        assert advanced.usage.total() == 5
        assert advanced.task_id == "t-1"


def test_fresh_context_is_idle_with_no_pending_actions():
        context = _started()
        assert context.state() is ExecutionState.IDLE
        assert not context.has_pending_actions()
        assert context.final_output() is None


def test_with_assistant_records_turn_pending_calls_and_usage():
        call = ToolCall(id="c1", name="echo", arguments={"text": "hi"})
        completion = Completion(
                content="let me echo",
                tool_calls=(call,),
                usage=TokenUsage(prompt_tokens=4, completion_tokens=1),
        )

        context = _started().with_assistant(completion)

        assert context.state() is ExecutionState.REASONING
        assert context.has_pending_actions()
        assert tuple(context.pending_tool_calls()) == (call,)
        assert context.metadata().usage.total() == 5
        assert context.current_conversation().last() == Message.assistant("let me echo", (call,))


def test_model_turn_advances_iteration_and_observation_folds_results():
        call = ToolCall(id="c1", name="echo", arguments={"text": "hi"})
        context = _started().with_assistant(Completion(tool_calls=(call,)))
        assert context.metadata().iterations == 1  # one model call == one iteration

        result = ToolResult.success(call_id="c1", tool_name="echo", content="hi")
        context = context.with_tool_results([result])
        assert context.state() is ExecutionState.ACTING

        context = context.observed()
        assert context.state() is ExecutionState.OBSERVING
        assert not context.has_pending_actions()
        assert context.metadata().iterations == 1  # observation folds, doesn't re-count
        # The observation is now part of the conversation as a TOOL message.
        last = context.current_conversation().last()
        assert last is not None
        assert last.role is Role.TOOL
        assert last.content == "hi"


def test_cycle_signature_is_stable_for_equal_action_and_observation():
        call = ToolCall(id="c1", name="echo", arguments={"text": "hi"})
        result = ToolResult.success(call_id="c1", tool_name="echo", content="hi")

        a = _started().with_assistant(Completion(tool_calls=(call,))).with_tool_results([result])
        b = _started().with_assistant(Completion(tool_calls=(call,))).with_tool_results([result])

        assert a.cycle_signature() == b.cycle_signature()
        assert a.cycle_signature() != _started().cycle_signature()


def test_stopped_and_aborted_reach_terminal_states():
        stopped = _started().stopped("the answer")
        assert stopped.state() is ExecutionState.COMPLETED
        assert stopped.state().is_terminal()
        assert stopped.final_output() == "the answer"

        aborted = _started().aborted()
        assert aborted.state() is ExecutionState.ABORTED
        assert aborted.state().is_terminal()


def test_execution_result_reports_success_from_context():
        context = _started().stopped("done")
        result = ExecutionResult.from_context(context, stop_reason="model answered")

        assert result.succeeded()
        assert result.final_output == "done"
        assert result.stop_reason == "model answered"


def test_execution_result_from_aborted_context_is_not_success():
        result = ExecutionResult.from_context(_started().aborted(), stop_reason="iteration cap")
        assert not result.succeeded()
        assert result.state is ExecutionState.ABORTED
