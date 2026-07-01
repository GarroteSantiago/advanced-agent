"""Value objects for the LLM conversation domain.

These are pure, immutable value objects shared across the harness. Behavior
that belongs to the data lives here -- ``Conversation`` owns how messages
accumulate, ``Completion`` knows whether it is asking for tools, ``TokenUsage``
knows how to total and combine -- so collaborators never reach into raw lists.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum

ToolSchema = Mapping[str, object]
"""A single provider-neutral tool schema (name, description, parameters).

This is the only thing a ``ChatModel`` needs to know about tools, which keeps
the model port from depending on the harness's tool subsystem.
"""


class Role(StrEnum):
        """Authorship of a message, as understood by chat models."""

        SYSTEM = "system"
        USER = "user"
        ASSISTANT = "assistant"
        TOOL = "tool"


@dataclass(frozen=True, slots=True)
class ToolCall:
        """A model's request to invoke a named tool with arguments."""

        id: str
        name: str
        arguments: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Message:
        """A single turn in a conversation.

        Constructed through the role-named factories rather than positionally,
        so callers state intent ("a tool result", "an assistant turn") instead
        of juggling optional fields.
        """

        role: Role
        content: str = ""
        tool_calls: tuple[ToolCall, ...] = ()
        tool_call_id: str | None = None
        name: str | None = None

        @classmethod
        def system(cls, content: str) -> Message:
                return cls(role=Role.SYSTEM, content=content)

        @classmethod
        def user(cls, content: str) -> Message:
                return cls(role=Role.USER, content=content)

        @classmethod
        def assistant(
                cls,
                content: str = "",
                tool_calls: tuple[ToolCall, ...] = (),
        ) -> Message:
                return cls(role=Role.ASSISTANT, content=content, tool_calls=tool_calls)

        @classmethod
        def tool(cls, content: str, *, tool_call_id: str, name: str | None = None) -> Message:
                return cls(
                        role=Role.TOOL,
                        content=content,
                        tool_call_id=tool_call_id,
                        name=name,
                )


@dataclass(frozen=True, slots=True)
class TokenUsage:
        """Token accounting for a single model call, summable across calls."""

        prompt_tokens: int = 0
        completion_tokens: int = 0

        def total(self) -> int:
                return self.prompt_tokens + self.completion_tokens

        def __add__(self, other: TokenUsage) -> TokenUsage:
                return TokenUsage(
                        prompt_tokens=self.prompt_tokens + other.prompt_tokens,
                        completion_tokens=self.completion_tokens + other.completion_tokens,
                )


@dataclass(frozen=True, slots=True)
class Completion:
        """What a chat model produced for one call.

        ``requests_tools`` is the question the loop actually asks; keeping it on
        the completion stops that decision from leaking into the phases as a raw
        ``len(...)`` check.
        """

        content: str = ""
        tool_calls: tuple[ToolCall, ...] = ()
        stop_reason: str | None = None
        usage: TokenUsage = field(default_factory=TokenUsage)

        def requests_tools(self) -> bool:
                return bool(self.tool_calls)


@dataclass(frozen=True, slots=True)
class Conversation:
        """An immutable, append-only sequence of messages.

        The backing tuple is never exposed for in-place modification: growth
        returns a new ``Conversation`` and ``messages`` hands back an immutable
        view. Build one with ``empty``/``of`` rather than the underscore field.
        """

        _messages: tuple[Message, ...] = ()

        @classmethod
        def empty(cls) -> Conversation:
                return cls()

        @classmethod
        def of(cls, messages: Iterable[Message]) -> Conversation:
                return cls(tuple(messages))

        def with_message(self, message: Message) -> Conversation:
                return Conversation((*self._messages, message))

        def with_messages(self, messages: Iterable[Message]) -> Conversation:
                return Conversation((*self._messages, *messages))

        def messages(self) -> Sequence[Message]:
                return self._messages

        def last(self) -> Message | None:
                return self._messages[-1] if self._messages else None

        def __len__(self) -> int:
                return len(self._messages)

        def __iter__(self) -> Iterator[Message]:
                return iter(self._messages)
