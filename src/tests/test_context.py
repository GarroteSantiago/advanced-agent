"""Tests for the context-management seam."""

from harness.context import ContextManager
from llm import Conversation, Message


def test_context_manager_is_a_pass_through_for_now():
        conversation = Conversation.of([Message.system("s"), Message.user("u")])
        assert ContextManager().prepare(conversation) is conversation
