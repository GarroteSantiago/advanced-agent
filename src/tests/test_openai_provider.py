"""Offline tests for the OpenAI translation layer (no network)."""

import json
from types import SimpleNamespace

from llm import Conversation, Message, Role, ToolCall
from llm.providers.openai_model import decode_completion, encode_messages, encode_tools


def test_encode_messages_maps_each_role():
        convo = Conversation.of(
                [
                        Message.system("sys"),
                        Message.user("hi"),
                        Message.assistant(
                                "thinking",
                                (ToolCall(id="c1", name="echo", arguments={"text": "x"}),),
                        ),
                        Message.tool("observed", tool_call_id="c1", name="echo"),
                ]
        )

        encoded = encode_messages(convo)

        assert encoded[0]["role"] == "system"
        assert encoded[1] == {"role": "user", "content": "hi"}
        assert encoded[2]["role"] == "assistant"
        call = encoded[2]["tool_calls"][0]
        assert call["id"] == "c1"
        assert call["function"]["name"] == "echo"
        assert json.loads(call["function"]["arguments"]) == {"text": "x"}
        assert encoded[3] == {"role": "tool", "tool_call_id": "c1", "content": "observed"}


def test_encode_tools_wraps_schema_as_function():
        encoded = encode_tools([{"name": "echo", "description": "d", "parameters": {"type": "object"}}])
        assert encoded[0]["type"] == "function"
        assert encoded[0]["function"]["name"] == "echo"
        assert encoded[0]["function"]["parameters"] == {"type": "object"}


def test_decode_text_completion():
        message = SimpleNamespace(content="the answer", tool_calls=None)
        usage = SimpleNamespace(prompt_tokens=4, completion_tokens=6)

        completion = decode_completion(message, usage, "stop")

        assert completion.content == "the answer"
        assert not completion.requests_tools()
        assert completion.usage.total() == 10
        assert completion.stop_reason == "stop"


def test_decode_tool_call_completion():
        call = SimpleNamespace(id="c1", function=SimpleNamespace(name="echo", arguments='{"text": "x"}'))
        message = SimpleNamespace(content=None, tool_calls=[call])

        completion = decode_completion(message, None, "tool_calls")

        assert completion.requests_tools()
        assert completion.tool_calls[0].name == "echo"
        assert completion.tool_calls[0].arguments == {"text": "x"}
        assert completion.content == ""  # None content normalizes to empty string


def test_decode_handles_blank_tool_arguments():
        call = SimpleNamespace(id="c1", function=SimpleNamespace(name="ping", arguments=""))
        message = SimpleNamespace(content=None, tool_calls=[call])

        completion = decode_completion(message, None, "tool_calls")
        assert completion.tool_calls[0].arguments == {}


def test_role_value_serialization():
        # Guards the assumption encode_messages relies on for system/user turns.
        assert Role.SYSTEM.value == "system"
        assert Role.USER.value == "user"
