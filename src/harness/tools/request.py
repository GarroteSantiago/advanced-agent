"""A request to invoke a tool, derived from a model's tool call."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ToolRequest:
        """An immutable instruction handed to a tool's ``invoke``."""

        call_id: str
        tool_name: str
        arguments: Mapping[str, object] = field(default_factory=dict)
