"""The tool registry: the harness's record of which tools exist."""

from __future__ import annotations

from collections.abc import Sequence

from harness.tools.catalog import ToolCatalog
from harness.tools.tool import ToolInterface


class ToolError(Exception):
        """Base class for tool-registry errors."""


class DuplicateToolError(ToolError):
        def __init__(self, name: str) -> None:
                super().__init__(f"a tool named {name!r} is already registered")
                self.name = name


class UnknownToolError(ToolError):
        def __init__(self, name: str) -> None:
                super().__init__(f"no tool named {name!r} is registered")
                self.name = name


class ToolRegistry:
        """An encapsulated name -> tool map; the only way tools are looked up."""

        def __init__(self) -> None:
                self._tools: dict[str, ToolInterface] = {}

        def register(self, tool: ToolInterface) -> None:
                if tool.name in self._tools:
                        raise DuplicateToolError(tool.name)
                self._tools[tool.name] = tool

        def get(self, name: str) -> ToolInterface:
                try:
                        return self._tools[name]
                except KeyError:
                        raise UnknownToolError(name) from None

        def has(self, name: str) -> bool:
                return name in self._tools

        def tools(self) -> Sequence[ToolInterface]:
                return tuple(self._tools.values())

        def catalog(self) -> ToolCatalog:
                return ToolCatalog.of_tools(self._tools.values())

        def __len__(self) -> int:
                return len(self._tools)
