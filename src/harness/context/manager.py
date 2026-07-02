"""Context management: deciding what enters the model's window.

``ContextManager`` is a read-time projection: given the full, immutable
conversation it returns the (possibly smaller) view to send to the model this
turn. It never mutates or truncates the persisted history -- the context keeps
the whole record, and each reason turn re-projects it -- so summarization stays
non-destructive and the ledger remains the durable home of decisions.

The policy here is structural *windowing*, not semantic summarization: once the
conversation exceeds ``max_messages`` it keeps the leading instructions and the
original task, elides the middle behind a marker, and keeps the most recent
``keep_recent`` turns verbatim. The elision boundary is chosen so it never
orphans a tool result (a ``tool`` message whose assistant ``tool_calls`` was
dropped), which the model providers reject. A model-based ``Summarizer`` that
turns the elided span into prose (rather than a marker) is the natural next
seam; the durable facts it would preserve already live in the ``TaskLedger``.
"""

from __future__ import annotations

from collections.abc import Sequence

from llm import Conversation, Message, Role


class ContextManager:
        """Windows the conversation handed to the model, preserving correctness."""

        def __init__(self, *, max_messages: int = 40, keep_recent: int = 12) -> None:
                if keep_recent < 1:
                        raise ValueError("keep_recent must be at least 1")
                if max_messages <= keep_recent:
                        raise ValueError("max_messages must exceed keep_recent")
                self._max_messages = max_messages
                self._keep_recent = keep_recent

        def prepare(self, conversation: Conversation) -> Conversation:
                messages = conversation.messages()
                if len(messages) <= self._max_messages:
                        return conversation

                head = self._head(messages)
                start = self._safe_tail_start(messages, head_len=len(head))
                if start <= len(head) or start >= len(messages):
                        return conversation  # nothing can be safely elided

                elided = start - len(head)
                marker = Message.system(
                        f"[{elided} earlier messages elided to fit the context window; "
                        "durable facts are recorded in the task ledger]"
                )
                return Conversation.of((*head, marker, *messages[start:]))

        def _head(self, messages: Sequence[Message]) -> tuple[Message, ...]:
                """The leading instructions plus the original task, always kept."""
                head: list[Message] = []
                index = 0
                while index < len(messages) and messages[index].role is Role.SYSTEM:
                        head.append(messages[index])
                        index += 1
                if index < len(messages) and messages[index].role is Role.USER:
                        head.append(messages[index])  # the original request
                return tuple(head)

        def _safe_tail_start(self, messages: Sequence[Message], *, head_len: int) -> int:
                """The earliest tail index that does not orphan a tool result.

                A ``tool`` message whose assistant ``tool_calls`` has been elided is
                invalid, so the tail may not begin on one; step forward past any such
                leading tool results to the next self-contained turn.
                """
                start = max(len(messages) - self._keep_recent, head_len)
                while start < len(messages) and messages[start].role is Role.TOOL:
                        start += 1
                return start
