"""The provider-neutral view of the available tools.

``ToolCatalog`` is the boundary between the harness's tools and the model: it
renders each tool to a ``ToolSchema`` the model can reason about, and owns the
shape of that schema so no other component encodes it.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from harness.tools.tool import Describable
from llm import ToolSchema


@dataclass(frozen=True, slots=True)
class ToolCatalog:
        """An immutable set of tool schemas ready to hand to a ``ChatModel``."""

        _schemas: tuple[ToolSchema, ...] = ()

        @classmethod
        def of_tools(cls, tools: Iterable[Describable]) -> ToolCatalog:
                return cls(tuple(cls._render(tool) for tool in tools))

        @staticmethod
        def _render(tool: Describable) -> ToolSchema:
                return {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters(),
                }

        def for_model(self) -> Sequence[ToolSchema]:
                return self._schemas

        def is_empty(self) -> bool:
                return not self._schemas

        def __len__(self) -> int:
                return len(self._schemas)
