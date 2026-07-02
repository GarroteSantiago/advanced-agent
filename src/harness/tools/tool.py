"""The tool port.

A tool is an autonomous collaborator that perceives or alters the environment.
It advertises a name, a description, and a parameter schema (so the model can
decide to call it), and it knows how to invoke itself. Concrete tools live in
``harness.tools.adapters``.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, runtime_checkable

from harness.tools.request import ToolRequest
from harness.tools.result import ToolResult


@runtime_checkable
class Describable(Protocol):
        """Anything the model can be told about: a name, a description, a schema.

        Both tools and subagents are ``Describable``, so a single ``ToolCatalog``
        can render either into a schema the model reasons over.
        """

        @property
        def name(self) -> str: ...

        @property
        def description(self) -> str: ...

        def parameters(self) -> Mapping[str, object]: ...


@runtime_checkable
class ToolInterface(Describable, Protocol):
        """A named, self-describing, invokable capability."""

        @property
        def mutates(self) -> bool:
                """Whether invoking this tool changes the world. Read-only tools
                run freely; mutating tools are what supervision gates."""
                ...

        async def invoke(self, request: ToolRequest) -> ToolResult: ...
