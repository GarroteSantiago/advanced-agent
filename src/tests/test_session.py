"""Tests for the conversational Session: history persists across turns."""

from agent import Session
from harness.tools import SupervisionPolicy
from harness.tools.adapters import WriteFileTool
from llm import Completion, Conversation, Role, ToolCall
from tests.doubles import FakeChatModel


class _DenyingConfirmer:
        async def confirm(self, request) -> bool:
                return False


async def test_history_persists_across_turns():
        model = FakeChatModel([Completion(content="hi there"), Completion(content="you said hello")])
        session = Session(model)

        await session.ask("hello")
        await session.ask("what did I say?")

        # The second model call must see the first turn's user + assistant messages.
        second_turn_conversation: Conversation = model.calls[1][0]
        contents = [(m.role, m.content) for m in second_turn_conversation]
        assert (Role.USER, "hello") in contents
        assert (Role.ASSISTANT, "hi there") in contents
        assert (Role.USER, "what did I say?") in contents


async def test_session_conversation_grows_with_each_turn():
        model = FakeChatModel([Completion(content="a"), Completion(content="b")])
        session = Session(model)

        await session.ask("first")
        after_one = len(session.conversation())
        await session.ask("second")
        after_two = len(session.conversation())

        assert after_two > after_one


async def test_supervision_through_session_blocks_a_declined_write(tmp_path):
        target = tmp_path / "guarded.txt"
        model = FakeChatModel(
                [
                        Completion(
                                tool_calls=(
                                        ToolCall(
                                                id="c1",
                                                name="write_file",
                                                arguments={"path": str(target), "content": "x"},
                                        ),
                                )
                        ),
                        Completion(content="I was not allowed to write."),
                ]
        )
        session = Session(
                model,
                tools=[WriteFileTool()],
                approver=SupervisionPolicy(_DenyingConfirmer(), enabled=True),
        )

        result = await session.ask("write the file")

        assert result.succeeded()
        assert not target.exists()  # supervision blocked the side effect
        # The decline came back to the model as a TOOL observation.
        tool_messages = [m for m in result.conversation if m.role is Role.TOOL]
        assert any("declined" in m.content for m in tool_messages)


async def test_tools_are_offered_to_the_model():
        model = FakeChatModel([Completion(content="done")])
        session = Session(model, tools=[WriteFileTool()])

        await session.ask("hi")

        offered = model.calls[0][1]
        assert offered is not None
        assert any(schema["name"] == "write_file" for schema in offered)
