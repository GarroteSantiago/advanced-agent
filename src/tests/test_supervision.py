"""Tests for human-in-the-loop supervision of tool execution."""

from harness.tools import (
        AutoApprover,
        SupervisionPolicy,
        ToolExecutor,
        ToolRegistry,
        ToolRequest,
)
from harness.tools.adapters import ReadFileTool, WriteFileTool
from llm import ToolCall


class _FakeConfirmer:
        def __init__(self, answer: bool) -> None:
                self._answer = answer
                self.asked: list[ToolRequest] = []

        async def confirm(self, request: ToolRequest) -> bool:
                self.asked.append(request)
                return self._answer


async def test_auto_approver_allows_everything():
        request = ToolRequest(call_id="c1", tool_name="write_file")
        assert (await AutoApprover().review(request, mutating=True)).allowed


async def test_disabled_supervision_allows_mutating_actions():
        confirmer = _FakeConfirmer(answer=False)
        policy = SupervisionPolicy(confirmer, enabled=False)

        request = ToolRequest(call_id="c1", tool_name="write_file")
        assert (await policy.review(request, mutating=True)).allowed
        assert confirmer.asked == []  # never consulted while disabled


async def test_enabled_supervision_skips_confirmation_for_read_only():
        confirmer = _FakeConfirmer(answer=False)
        policy = SupervisionPolicy(confirmer, enabled=True)

        request = ToolRequest(call_id="c1", tool_name="read_file")
        assert (await policy.review(request, mutating=False)).allowed
        assert confirmer.asked == []  # read-only never prompts


async def test_enabled_supervision_denies_when_user_declines():
        confirmer = _FakeConfirmer(answer=False)
        policy = SupervisionPolicy(confirmer, enabled=True)

        request = ToolRequest(call_id="c1", tool_name="write_file")
        verdict = await policy.review(request, mutating=True)
        assert verdict.denied()
        assert "declined" in verdict.reason
        assert len(confirmer.asked) == 1


async def test_declined_mutating_tool_is_not_executed(tmp_path):
        target = tmp_path / "guarded.txt"
        registry = ToolRegistry()
        registry.register(WriteFileTool())
        executor = ToolExecutor(
                registry, approver=SupervisionPolicy(_FakeConfirmer(answer=False), enabled=True)
        )

        result = await executor.execute(
                ToolCall(id="c1", name="write_file", arguments={"path": str(target), "content": "x"})
        )

        assert not result.ok
        assert "declined" in (result.error or "")
        assert not target.exists()  # the side effect never happened


async def test_read_only_tool_runs_under_supervision(tmp_path):
        source = tmp_path / "in.txt"
        source.write_text("hi", encoding="utf-8")
        registry = ToolRegistry()
        registry.register(ReadFileTool())
        confirmer = _FakeConfirmer(answer=False)  # would deny, but read-only isn't asked
        executor = ToolExecutor(registry, approver=SupervisionPolicy(confirmer, enabled=True))

        result = await executor.execute(
                ToolCall(id="c1", name="read_file", arguments={"path": str(source)})
        )

        assert result.ok
        assert result.content == "hi"
        assert confirmer.asked == []
