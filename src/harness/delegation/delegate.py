"""The delegation port and the principal's roster of subagents.

A ``Delegate`` is anything the principal can hand a task to and get a
``SubagentReport`` back. It is ``Describable`` (name/description/parameters), so
the principal's ``ToolCatalog`` renders it to the model exactly like a tool --
that is how the model comes to *choose* delegation via an ordinary tool call.
Concrete delegates (the five subagents) live outward in the ``agent`` layer.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Protocol, runtime_checkable

from harness.delegation.report import SubagentReport


class UnknownSubagentError(KeyError):
        def __init__(self, name: str) -> None:
                super().__init__(f"no subagent named {name!r} is registered")


@runtime_checkable
class Delegate(Protocol):
        """A subagent the principal can delegate a task to."""

        @property
        def name(self) -> str: ...

        @property
        def description(self) -> str: ...

        def parameters(self) -> Mapping[str, object]: ...

        async def delegate(self, task: str) -> SubagentReport: ...


class SubagentRegistry:
        """The principal's roster: resolves a call name to its subagent."""

        def __init__(self, subagents: Iterable[Delegate] = ()) -> None:
                self._by_name: dict[str, Delegate] = {}
                for subagent in subagents:
                        self._by_name[subagent.name] = subagent

        def knows(self, name: str) -> bool:
                return name in self._by_name

        def resolve(self, name: str) -> Delegate:
                try:
                        return self._by_name[name]
                except KeyError as error:
                        raise UnknownSubagentError(name) from error

        def all(self) -> Sequence[Delegate]:
                return tuple(self._by_name.values())
