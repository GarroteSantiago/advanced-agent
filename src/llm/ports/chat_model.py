"""The chat model port.

``ChatModel`` is the single abstraction the harness depends on to talk to a
language model. It is a structural port (``Protocol``): concrete providers live
outward in ``llm.providers`` and are wired in at the composition root. The port
is message-oriented (it speaks ``Conversation``/``Completion``), which is why it
can express tool use -- replacing the earlier anemic ``send(str) -> str``.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from llm.messages import Completion, Conversation, ToolSchema


@runtime_checkable
class ChatModel(Protocol):
        """A language model that completes a conversation, optionally with tools.

        ``tools`` are already-rendered, provider-neutral schemas (see
        ``ToolCatalog.for_model``); the model decides whether to answer directly
        or to emit ``tool_calls`` on the returned ``Completion``.
        """

        def identifier(self) -> str:
                """The model's own name (e.g. ``gpt-5-nano``), for observability."""
                ...

        async def complete(
                self,
                conversation: Conversation,
                *,
                tools: Sequence[ToolSchema] | None = None,
        ) -> Completion: ...
