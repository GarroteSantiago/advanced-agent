"""read_file: read the contents of a file at a given path (read-only)."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from harness.tools.request import ToolRequest
from harness.tools.result import ToolResult


class ReadFileTool:
        @property
        def name(self) -> str:
                return "read_file"

        @property
        def description(self) -> str:
                return "Read the full contents of a file at the given path."

        @property
        def mutates(self) -> bool:
                return False

        def parameters(self) -> Mapping[str, object]:
                return {
                        "type": "object",
                        "properties": {"path": {"type": "string"}},
                        "required": ["path"],
                }

        async def invoke(self, request: ToolRequest) -> ToolResult:
                path = request.arguments.get("path")
                if not isinstance(path, str):
                        return ToolResult.failure(
                                call_id=request.call_id,
                                tool_name=self.name,
                                error="read_file requires a string 'path' argument",
                        )
                try:
                        content = Path(path).read_text(encoding="utf-8")
                except OSError as error:
                        return ToolResult.failure(
                                call_id=request.call_id, tool_name=self.name, error=str(error)
                        )
                return ToolResult.success(
                        call_id=request.call_id, tool_name=self.name, content=content
                )
