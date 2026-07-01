"""list_files: list the entries of a directory (read-only)."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from harness.tools.request import ToolRequest
from harness.tools.result import ToolResult


class ListFilesTool:
        @property
        def name(self) -> str:
                return "list_files"

        @property
        def description(self) -> str:
                return "List the entries in a directory (defaults to the current directory)."

        @property
        def mutates(self) -> bool:
                return False

        def parameters(self) -> Mapping[str, object]:
                return {
                        "type": "object",
                        "properties": {"path": {"type": "string"}},
                        "required": [],
                }

        async def invoke(self, request: ToolRequest) -> ToolResult:
                raw = request.arguments.get("path", ".")
                path = raw if isinstance(raw, str) else "."
                directory = Path(path)
                if not directory.is_dir():
                        return ToolResult.failure(
                                call_id=request.call_id,
                                tool_name=self.name,
                                error=f"{path!r} is not a directory",
                        )
                entries = sorted(
                        entry.name + ("/" if entry.is_dir() else "")
                        for entry in directory.iterdir()
                )
                return ToolResult.success(
                        call_id=request.call_id,
                        tool_name=self.name,
                        content="\n".join(entries),
                )
