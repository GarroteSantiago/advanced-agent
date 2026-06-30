"""A trivial tool used for tests and smoke runs: it echoes its ``text`` argument."""

from __future__ import annotations

from collections.abc import Mapping

from harness.tools.request import ToolRequest
from harness.tools.result import ToolResult


class EchoTool:
        """Returns its ``text`` argument verbatim. Conforms to ``ToolInterface``."""

        @property
        def name(self) -> str:
                return "echo"

        @property
        def description(self) -> str:
                return "Echo the provided text back unchanged."

        @property
        def mutates(self) -> bool:
                return False

        def parameters(self) -> Mapping[str, object]:
                return {
                        "type": "object",
                        "properties": {"text": {"type": "string"}},
                        "required": ["text"],
                }

        async def invoke(self, request: ToolRequest) -> ToolResult:
                text = request.arguments.get("text")
                if not isinstance(text, str):
                        return ToolResult.failure(
                                call_id=request.call_id,
                                tool_name=self.name,
                                error="echo requires a string 'text' argument",
                        )
                return ToolResult.success(
                        call_id=request.call_id,
                        tool_name=self.name,
                        content=text,
                )
