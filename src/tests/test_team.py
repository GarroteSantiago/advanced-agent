"""Tests for the subagent team factory."""

from __future__ import annotations

from pathlib import Path

from agent.team import build_subagents
from llm import Completion, ToolCall
from tests.doubles import FakeChatModel


def test_build_subagents_registers_the_six_roles() -> None:
        registry = build_subagents(FakeChatModel([]))

        names = {delegate.name for delegate in registry.all()}
        assert names == {"explore", "research", "implement", "test", "review", "scribe"}


def test_each_subagent_exposes_a_task_parameter() -> None:
        registry = build_subagents(FakeChatModel([]))

        for delegate in registry.all():
                schema = delegate.parameters()
                properties = schema["properties"]
                assert "task" in properties  # type: ignore[operator]


async def test_the_scribe_writes_inside_the_docs_folder_but_is_blocked_outside(tmp_path) -> None:
        docs = tmp_path / "docs"
        inside = str(docs / "explore.md")
        outside = str(tmp_path / "escape.md")
        # The Scribe tries an in-folder write (allowed), then an out-of-folder write
        # (must be refused by its confinement policy), then answers.
        model = FakeChatModel(
                [
                        Completion(
                                tool_calls=(
                                        ToolCall(
                                                id="c1",
                                                name="write_file",
                                                arguments={"path": inside, "content": "explore findings"},
                                        ),
                                )
                        ),
                        Completion(
                                tool_calls=(
                                        ToolCall(
                                                id="c2",
                                                name="write_file",
                                                arguments={"path": outside, "content": "nope"},
                                        ),
                                )
                        ),
                        Completion(content="wrote explore.md"),
                ]
        )
        registry = build_subagents(model, docs_dir=docs)

        report = await registry.resolve("scribe").delegate("document the explore findings")

        assert Path(inside).read_text(encoding="utf-8") == "explore findings"
        assert not Path(outside).exists()  # confinement blocked the out-of-folder write
        assert report.modified_files == (inside,)  # only the permitted write was recorded


async def test_only_the_scribe_can_write(tmp_path) -> None:
        # A read-only role (explore) has no write_file tool at all: a write call
        # comes back as an unknown-tool failure, and nothing is recorded.
        model = FakeChatModel(
                [
                        Completion(
                                tool_calls=(
                                        ToolCall(
                                                id="c1",
                                                name="write_file",
                                                arguments={"path": str(tmp_path / "x.md"), "content": "no"},
                                        ),
                                )
                        ),
                        Completion(content="cannot write"),
                ]
        )
        registry = build_subagents(model, docs_dir=tmp_path)

        report = await registry.resolve("explore").delegate("try to write")

        assert not (tmp_path / "x.md").exists()
        assert report.modified_files == ()
