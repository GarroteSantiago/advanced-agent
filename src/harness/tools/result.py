"""The outcome of a tool invocation.

``ToolResult`` carries behavior, not just data: it knows how to render itself as
a TOOL observation message (``to_message``), so the observation phase never has
to know the shape of a tool message.
"""

from __future__ import annotations

from dataclasses import dataclass

from llm import Message


@dataclass(frozen=True, slots=True)
class ToolResult:
        """What a tool produced (or failed to produce) for one call.

        ``modified`` names the files this call changed, so the loop can record
        them in the shared ledger without parsing the human-readable ``content``:
        the tool -- which alone knows what it altered -- reports it as data.
        """

        call_id: str
        tool_name: str
        ok: bool
        content: str = ""
        error: str | None = None
        modified: tuple[str, ...] = ()

        @classmethod
        def success(
                cls,
                *,
                call_id: str,
                tool_name: str,
                content: str,
                modified: tuple[str, ...] = (),
        ) -> ToolResult:
                return cls(
                        call_id=call_id,
                        tool_name=tool_name,
                        ok=True,
                        content=content,
                        modified=modified,
                )

        @classmethod
        def failure(cls, *, call_id: str, tool_name: str, error: str) -> ToolResult:
                return cls(call_id=call_id, tool_name=tool_name, ok=False, error=error)

        def to_message(self) -> Message:
                body = self.content if self.ok else (self.error or "tool failed")
                return Message.tool(body, tool_call_id=self.call_id, name=self.tool_name)
