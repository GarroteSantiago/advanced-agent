"""Config-driven guardrails, validated before every tool call.

``PolicyConfig`` is loaded from a TOML file (stdlib ``tomllib`` -- no dependency).
``PolicyVerifier`` is an ``Approver`` that maps a tool call to the relevant rule:
file tools' ``path`` against read/write deny-globs and the workspace boundary;
``run_command``'s ``command`` against forbidden patterns and the
require-approval list.

Caveats (state them, don't hide them): glob matching uses ``fnmatch`` semantics
(``*`` spans separators); command matching is substring-based and therefore
best-effort -- a guardrail, not a sandbox. Rules fail closed.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path

from harness.tools.approval import Approval, Confirmer
from harness.tools.request import ToolRequest

_READ_PATH_TOOLS = frozenset({"read_file", "list_files"})
_WRITE_PATH_TOOLS = frozenset({"write_file"})
_COMMAND_TOOLS = frozenset({"run_command"})


@dataclass(frozen=True, slots=True)
class PolicyConfig:
        """Declarative guardrails for the agent."""

        workspace: Path | None = None
        read_deny: tuple[str, ...] = ()
        write_deny: tuple[str, ...] = ()
        command_deny: tuple[str, ...] = ()
        command_require_approval: tuple[str, ...] = ()

        @classmethod
        def empty(cls) -> PolicyConfig:
                return cls()

        @classmethod
        def from_toml(cls, path: Path) -> PolicyConfig:
                data = tomllib.loads(path.read_text(encoding="utf-8"))
                permissions = data.get("permissions", {})
                read = permissions.get("read", {})
                write = permissions.get("write", {})
                commands = data.get("commands", {})
                workspace = data.get("workspace")
                return cls(
                        workspace=Path(workspace) if isinstance(workspace, str) else None,
                        read_deny=tuple(read.get("deny", [])),
                        write_deny=tuple(write.get("deny", [])),
                        command_deny=tuple(commands.get("deny", [])),
                        command_require_approval=tuple(commands.get("require_approval", [])),
                )


class PolicyVerifier:
        """Validates each tool call against a ``PolicyConfig``."""

        def __init__(self, config: PolicyConfig, confirmer: Confirmer | None = None) -> None:
                self._config = config
                self._confirmer = confirmer

        async def review(self, request: ToolRequest, *, mutating: bool) -> Approval:
                name = request.tool_name
                if name in _READ_PATH_TOOLS:
                        return self._check_path(request, self._config.read_deny)
                if name in _WRITE_PATH_TOOLS:
                        return self._check_path(request, self._config.write_deny)
                if name in _COMMAND_TOOLS:
                        return await self._check_command(request)
                return Approval.allow()

        def _check_path(self, request: ToolRequest, deny: tuple[str, ...]) -> Approval:
                raw = request.arguments.get("path")
                if not isinstance(raw, str):
                        return Approval.allow()  # let the tool report the malformed argument
                path = Path(raw)
                if self._config.workspace is not None and not self._within_workspace(path):
                        return Approval.deny(f"path {raw!r} is outside the workspace")
                matched = self._matches(path, deny)
                if matched is not None:
                        return Approval.deny(f"path {raw!r} is blocked by policy ({matched})")
                return Approval.allow()

        async def _check_command(self, request: ToolRequest) -> Approval:
                command = request.arguments.get("command")
                if not isinstance(command, str):
                        return Approval.allow()
                forbidden = _first_substring(command, self._config.command_deny)
                if forbidden is not None:
                        return Approval.deny(f"command blocked by policy ({forbidden})")
                needs = _first_substring(command, self._config.command_require_approval)
                if needs is not None and (
                        self._confirmer is None or not await self._confirmer.confirm(request)
                ):
                        return Approval.deny(f"command requires approval and was not confirmed ({needs})")
                return Approval.allow()

        def _within_workspace(self, path: Path) -> bool:
                assert self._config.workspace is not None
                root = self._config.workspace.resolve()
                resolved = path.resolve()
                return resolved == root or root in resolved.parents

        @staticmethod
        def _matches(path: Path, patterns: tuple[str, ...]) -> str | None:
                candidates = (path.as_posix(), path.name)
                for pattern in patterns:
                        if any(fnmatch(candidate, pattern) for candidate in candidates):
                                return pattern
                return None


def _first_substring(text: str, patterns: tuple[str, ...]) -> str | None:
        for pattern in patterns:
                if pattern in text:
                        return pattern
        return None
