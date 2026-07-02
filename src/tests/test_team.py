"""Tests for the subagent team factory."""

from __future__ import annotations

from agent.team import build_subagents
from tests.doubles import FakeChatModel


def test_build_subagents_registers_the_five_roles() -> None:
        registry = build_subagents(FakeChatModel([]))

        names = {delegate.name for delegate in registry.all()}
        assert names == {"explore", "research", "implement", "test", "review"}


def test_each_subagent_exposes_a_task_parameter() -> None:
        registry = build_subagents(FakeChatModel([]))

        for delegate in registry.all():
                schema = delegate.parameters()
                properties = schema["properties"]
                assert "task" in properties  # type: ignore[operator]
