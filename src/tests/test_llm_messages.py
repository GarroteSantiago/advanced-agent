"""Unit tests for the LLM conversation value objects."""

from llm import Completion, Conversation, Message, Role, TokenUsage, ToolCall


def test_role_serializes_as_its_wire_string():
        assert Role.USER == "user"
        assert str(Role.ASSISTANT) == "assistant"


def test_message_factories_set_role_and_fields():
        assert Message.system("s").role is Role.SYSTEM
        assert Message.user("hi").content == "hi"

        call = ToolCall(id="c1", name="echo", arguments={"text": "x"})
        assistant = Message.assistant("thinking", tool_calls=(call,))
        assert assistant.role is Role.ASSISTANT
        assert assistant.tool_calls == (call,)

        observation = Message.tool("done", tool_call_id="c1", name="echo")
        assert observation.role is Role.TOOL
        assert observation.tool_call_id == "c1"


def test_tool_call_arguments_default_to_empty_mapping():
        assert ToolCall(id="c1", name="echo").arguments == {}


def test_token_usage_totals_and_adds():
        a = TokenUsage(prompt_tokens=10, completion_tokens=5)
        b = TokenUsage(prompt_tokens=1, completion_tokens=2)

        assert a.total() == 15
        combined = a + b
        assert combined == TokenUsage(prompt_tokens=11, completion_tokens=7)
        # Operands are unchanged (value semantics).
        assert a.total() == 15


def test_completion_knows_when_it_requests_tools():
        assert not Completion(content="answer").requests_tools()
        assert Completion(tool_calls=(ToolCall(id="c1", name="echo"),)).requests_tools()


def test_completion_defaults_to_zero_usage():
        assert Completion().usage == TokenUsage()


def test_conversation_is_append_only_and_does_not_mutate_in_place():
        base = Conversation.empty()
        grown = base.with_message(Message.user("hi"))

        assert len(base) == 0  # original untouched
        assert len(grown) == 1
        assert grown.last() == Message.user("hi")


def test_conversation_of_and_with_messages_accumulate_in_order():
        convo = Conversation.of([Message.system("s"), Message.user("u")])
        convo = convo.with_messages([Message.assistant("a"), Message.tool("t", tool_call_id="c1")])

        roles = [m.role for m in convo]
        assert roles == [Role.SYSTEM, Role.USER, Role.ASSISTANT, Role.TOOL]


def test_conversation_messages_view_is_immutable():
        convo = Conversation.of([Message.user("hi")])
        view = convo.messages()
        assert isinstance(view, tuple)  # cannot be mutated by callers


def test_empty_conversation_has_no_last():
        assert Conversation.empty().last() is None
