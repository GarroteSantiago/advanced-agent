"""Ports for user-facing I/O, so the agent never touches stdin/stdout directly.

``Renderer`` is the output port; ``Inputer`` is the input port. The console
implementations are the only place ``print``/``input`` are called -- everything
else depends on the ports, which is what makes the REPL testable.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class Renderer(Protocol):
        """Shows a line of text to the user."""

        def show(self, text: str) -> None: ...


@runtime_checkable
class Inputer(Protocol):
        """Reads a line from the user. Returns ``None`` at end of input (EOF)."""

        def read(self, prompt: str) -> str | None: ...


class ConsoleRenderer:
        def show(self, text: str) -> None:
                print(text)


class ConsoleInputer:
        def read(self, prompt: str) -> str | None:
                try:
                        return input(prompt)
                except EOFError:
                        return None
