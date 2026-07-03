"""Tests for the context-management seam: windowing what the model sees."""

from harness.context import ContextManager
from llm import Conversation, Message, Role, ToolCall


def _round(index: int) -> list[Message]:
        """One tool round: an assistant tool-call and its matching tool result."""
        call = ToolCall(id=f"c{index}", name="read_file", arguments={"path": f"f{index}.py"})
        return [
                Message.assistant(tool_calls=(call,)),
                Message.tool(f"contents {index}", tool_call_id=f"c{index}"),
        ]


def test_short_conversation_is_returned_unchanged() -> None:
        conversation = Conversation.of([Message.system("s"), Message.user("u")])
        # Identity (same object) below the threshold -- no needless copying.
        assert ContextManager().prepare(conversation) is conversation


def test_long_conversation_keeps_system_task_and_recent_and_elides_the_middle() -> None:
        messages = [Message.system("role"), Message.user("the original task")]
        for i in range(30):
                messages.extend(_round(i))
        conversation = Conversation.of(messages)

        prepared = ContextManager(max_messages=20, keep_recent=8).prepare(conversation)
        kept = prepared.messages()

        assert len(kept) < len(messages)  # history was trimmed
        assert kept[0] == Message.system("role")  # instructions preserved
        assert kept[1] == Message.user("the original task")  # original request preserved
        assert any("elided" in m.content for m in kept if m.role is Role.SYSTEM)  # a marker stands in
        assert kept[-1].content == "contents 29"  # most recent turn kept verbatim


def test_windowing_never_starts_the_tail_on_an_orphaned_tool_result() -> None:
        # If the naive cut lands between an assistant tool-call and its result,
        # the tail must not begin on the (now unpaired) tool message -- the
        # OpenAI API rejects a tool message without its preceding tool_calls.
        messages = [Message.system("role"), Message.user("task")]
        for i in range(30):
                messages.extend(_round(i))
        conversation = Conversation.of(messages)

        # keep_recent=7 is odd, so a naive tail would split a 2-message round.
        prepared = ContextManager(max_messages=20, keep_recent=7).prepare(conversation)
        kept = prepared.messages()

        # The marker is the boundary; the first message of the tail after it
        # must not be an orphaned tool result.
        marker_at = next(i for i, m in enumerate(kept) if "elided" in m.content)
        assert kept[marker_at + 1].role is not Role.TOOL
        # Every kept tool result still has its assistant tool_call immediately before it.
        for position, message in enumerate(kept):
                if message.role is Role.TOOL:
                        preceding = kept[position - 1]
                        assert preceding.role is Role.ASSISTANT
                        assert preceding.tool_calls


def test_rejects_incoherent_thresholds() -> None:
        import pytest

        with pytest.raises(ValueError, match="keep_recent"):
                ContextManager(keep_recent=0)
        with pytest.raises(ValueError, match="max_messages"):
                ContextManager(max_messages=5, keep_recent=5)
