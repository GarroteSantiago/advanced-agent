"""Reusable test doubles for the harness.

These are deliberately simple, fully-typed stand-ins so the gate's type checker
verifies they conform to the real ports (the typed annotations in tests force
that check).
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from llm import Completion, Conversation, ToolSchema


class FakeRenderer:
        """Captures shown lines instead of printing them."""

        def __init__(self) -> None:
                self.lines: list[str] = []

        def show(self, text: str) -> None:
                self.lines.append(text)


class FakeInputer:
        """Replays scripted inputs; returns None (EOF) once exhausted."""

        def __init__(self, *answers: str) -> None:
                self._answers: list[str] = list(answers)

        def read(self, prompt: str) -> str | None:
                return self._answers.pop(0) if self._answers else None


class FakeChatModel:
        """A scripted ``ChatModel``: returns queued completions in order.

        Records each conversation and the tool schemas it was offered, so tests
        can assert what the loop actually sent to the model.
        """

        def __init__(self, completions: Iterable[Completion]) -> None:
                self._scripted: list[Completion] = list(completions)
                self.calls: list[tuple[Conversation, Sequence[ToolSchema] | None]] = []

        async def complete(
                self,
                conversation: Conversation,
                *,
                tools: Sequence[ToolSchema] | None = None,
        ) -> Completion:
                self.calls.append((conversation, tools))
                if not self._scripted:
                        raise AssertionError("FakeChatModel ran out of scripted completions")
                return self._scripted.pop(0)
