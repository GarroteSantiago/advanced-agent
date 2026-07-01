"""Tests for the config-driven guardrails (PolicyConfig + PolicyVerifier)."""

from pathlib import Path

from harness.tools import (
        CompositeApprover,
        PolicyConfig,
        PolicyVerifier,
        ToolExecutor,
        ToolRegistry,
        ToolRequest,
)
from harness.tools.adapters import WriteFileTool
from llm import ToolCall

SAMPLE = """
workspace = "."
[permissions.read]
deny = [".env", "secrets/**"]
[permissions.write]
deny = ["uv.lock"]
[commands]
deny = ["rm -rf"]
require_approval = ["git commit"]
"""


class _Confirmer:
        def __init__(self, answer: bool) -> None:
                self._answer = answer

        async def confirm(self, request: ToolRequest) -> bool:
                return self._answer


def _req(tool: str, **arguments: object) -> ToolRequest:
        return ToolRequest(call_id="c1", tool_name=tool, arguments=arguments)


def test_from_toml_parses_all_sections(tmp_path):
        config_file = tmp_path / "agent.config.toml"
        config_file.write_text(SAMPLE, encoding="utf-8")

        config = PolicyConfig.from_toml(config_file)
        assert config.workspace == Path(".")
        assert config.read_deny == (".env", "secrets/**")
        assert config.write_deny == ("uv.lock",)
        assert config.command_deny == ("rm -rf",)
        assert config.command_require_approval == ("git commit",)


async def test_read_deny_blocks_matching_paths():
        verifier = PolicyVerifier(PolicyConfig(read_deny=(".env", "secrets/**")))

        assert (await verifier.review(_req("read_file", path=".env"), mutating=False)).denied()
        assert (await verifier.review(_req("read_file", path="secrets/key.txt"), mutating=False)).denied()
        assert (await verifier.review(_req("read_file", path="src/main.py"), mutating=False)).allowed


async def test_write_deny_blocks_matching_paths():
        verifier = PolicyVerifier(PolicyConfig(write_deny=("uv.lock",)))

        assert (await verifier.review(_req("write_file", path="uv.lock"), mutating=True)).denied()
        assert (await verifier.review(_req("write_file", path="notes.md"), mutating=True)).allowed


async def test_command_deny_blocks_forbidden_commands():
        verifier = PolicyVerifier(PolicyConfig(command_deny=("rm -rf",)))

        verdict = await verifier.review(_req("run_command", command="rm -rf /tmp/x"), mutating=True)
        assert verdict.denied()
        assert "policy" in verdict.reason
        assert (await verifier.review(_req("run_command", command="ls -la"), mutating=True)).allowed


async def test_workspace_confines_paths(tmp_path):
        verifier = PolicyVerifier(PolicyConfig(workspace=tmp_path))

        inside = tmp_path / "a.txt"
        assert (await verifier.review(_req("read_file", path=str(inside)), mutating=False)).allowed
        assert (await verifier.review(_req("read_file", path="/etc/passwd"), mutating=False)).denied()


async def test_require_approval_needs_confirmation():
        config = PolicyConfig(command_require_approval=("git commit",))

        declined = PolicyVerifier(config, _Confirmer(answer=False))
        assert (await declined.review(_req("run_command", command="git commit -m x"), mutating=True)).denied()

        accepted = PolicyVerifier(config, _Confirmer(answer=True))
        assert (await accepted.review(_req("run_command", command="git commit -m x"), mutating=True)).allowed


async def test_composite_first_denial_wins():
        deny_writes = PolicyVerifier(PolicyConfig(write_deny=("uv.lock",)))
        allow_all = PolicyVerifier(PolicyConfig())
        composite = CompositeApprover([deny_writes, allow_all])

        assert (await composite.review(_req("write_file", path="uv.lock"), mutating=True)).denied()
        assert (await composite.review(_req("write_file", path="ok.txt"), mutating=True)).allowed


async def test_policy_blocks_write_through_the_executor(tmp_path):
        target = tmp_path / "uv.lock"
        registry = ToolRegistry()
        registry.register(WriteFileTool())
        executor = ToolExecutor(registry, approver=PolicyVerifier(PolicyConfig(write_deny=("uv.lock",))))

        result = await executor.execute(
                ToolCall(id="c1", name="write_file", arguments={"path": str(target), "content": "x"})
        )

        assert not result.ok
        assert "policy" in (result.error or "")
        assert not target.exists()
