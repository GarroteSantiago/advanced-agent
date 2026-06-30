"""Tests for the ChatModel port and its scripted test double."""

import pytest

from llm import ChatModel, Completion, Conversation, Message, ToolCall
from tests.doubles import FakeChatModel


def test_fake_satisfies_chat_model_port():
        # The annotation makes pyright verify structural conformance; the
        # runtime_checkable Protocol lets us assert it here too.
        model: ChatModel = FakeChatModel([Completion(content="hi")])
        assert isinstance(model, ChatModel)


async def test_fake_returns_scripted_completions_in_order():
        first = Completion(tool_calls=(ToolCall(id="c1", name="echo"),))
        second = Completion(content="final")
        model = FakeChatModel([first, second])

        convo = Conversation.of([Message.user("hi")])
        assert await model.complete(convo) is first
        assert await model.complete(convo) is second


async def test_fake_records_conversations_and_offered_tools():
        model = FakeChatModel([Completion(content="ok")])
        convo = Conversation.of([Message.user("hi")])
        schemas = [{"name": "echo"}]

        await model.complete(convo, tools=schemas)

        assert model.calls == [(convo, schemas)]


async def test_fake_raises_when_script_exhausted():
        model = FakeChatModel([])
        with pytest.raises(AssertionError, match="ran out"):
                await model.complete(Conversation.empty())
