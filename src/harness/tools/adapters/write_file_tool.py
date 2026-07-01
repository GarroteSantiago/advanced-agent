"""write_file: write content to a file, replacing it (mutating)."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from harness.tools.request import ToolRequest
from harness.tools.result import ToolResult


class WriteFileTool:
        @property
        def name(self) -> str:
                return "write_file"

        @property
        def description(self) -> str:
                return "Write content to a file at the given path, replacing existing content."

        @property
        def mutates(self) -> bool:
                return True

        def parameters(self) -> Mapping[str, object]:
                return {
                        "type": "object",
                        "properties": {
                                "path": {"type": "string"},
                                "content": {"type": "string"},
                        },
                        "required": ["path", "content"],
                }

        async def invoke(self, request: ToolRequest) -> ToolResult:
                path = request.arguments.get("path")
                content = request.arguments.get("content")
                if not isinstance(path, str) or not isinstance(content, str):
                        return ToolResult.failure(
                                call_id=request.call_id,
                                tool_name=self.name,
                                error="write_file requires string 'path' and 'content' arguments",
                        )
                try:
                        Path(path).write_text(content, encoding="utf-8")
                except OSError as error:
                        return ToolResult.failure(
                                call_id=request.call_id, tool_name=self.name, error=str(error)
                        )
                return ToolResult.success(
                        call_id=request.call_id,
                        tool_name=self.name,
                        content=f"wrote {len(content)} characters to {path}",
                )
