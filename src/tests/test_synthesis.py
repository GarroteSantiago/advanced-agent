"""Tests for forced partial-findings synthesis on an unfinished run."""

from __future__ import annotations

from agent.synthesis import PartialSynthesizer
from harness.events import AuditLogger, EventBus, ModelCalled, ModelCompleted
from llm import Completion, Conversation, Message, Role
from tests.doubles import FakeChatModel


async def test_summarize_appends_a_recap_instruction_and_returns_the_content() -> None:
        model = FakeChatModel([Completion(content="Found routers; DB config unresolved.")])
        convo = Conversation.of([Message.user("analyze"), Message.assistant("looking…")])

        summary = await PartialSynthesizer(model).summarize(convo)

        assert summary == "Found routers; DB config unresolved."
        # It asked the model over the accumulated history plus a recap prompt,
        # and offered no tools (the recap must be prose, not another tool call).
        sent, tools = model.calls[-1]
        assert tools is None
        last = sent.last()
        assert last is not None
        assert last.role is Role.USER
        assert "summarize" in last.content.lower()


async def test_summarize_emits_model_events_for_observability() -> None:
        model = FakeChatModel([Completion(content="partial")])
        bus = EventBus()
        audit = AuditLogger()
        bus.subscribe(audit)

        await PartialSynthesizer(model, bus).summarize(Conversation.of([Message.user("x")]))

        kinds = [type(e) for e in audit.records()]
        assert ModelCalled in kinds
        assert ModelCompleted in kinds
