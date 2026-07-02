"""An OpenAI-backed ``ChatModel`` (outer-ring adapter).

Translates the harness's ``Conversation``/``ToolSchema`` into the OpenAI Chat
Completions format and the response back into a ``Completion``. The translation
lives in pure module functions (unit-tested without the network); ``Any`` is used
only at the untyped SDK boundary.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from openai import AsyncOpenAI

from llm.messages import Completion, Conversation, Role, TokenUsage, ToolCall, ToolSchema


def encode_messages(conversation: Conversation) -> list[Any]:
        encoded: list[Any] = []
        for message in conversation:
                if message.role is Role.ASSISTANT and message.tool_calls:
                        encoded.append(
                                {
                                        "role": "assistant",
                                        "content": message.content or None,
                                        "tool_calls": [
                                                {
                                                        "id": call.id,
                                                        "type": "function",
                                                        "function": {
                                                                "name": call.name,
                                                                "arguments": json.dumps(dict(call.arguments)),
                                                        },
                                                }
                                                for call in message.tool_calls
                                        ],
                                }
                        )
                elif message.role is Role.TOOL:
                        encoded.append(
                                {
                                        "role": "tool",
                                        "tool_call_id": message.tool_call_id,
                                        "content": message.content,
                                }
                        )
                else:
                        encoded.append({"role": message.role.value, "content": message.content})
        return encoded


def encode_tools(schemas: Sequence[ToolSchema]) -> list[Any]:
        return [
                {
                        "type": "function",
                        "function": {
                                "name": schema.get("name"),
                                "description": schema.get("description", ""),
                                "parameters": schema.get("parameters", {}),
                        },
                }
                for schema in schemas
        ]


def decode_completion(message: Any, usage: Any, finish_reason: str | None) -> Completion:
        tool_calls = tuple(
                ToolCall(
                        id=call.id,
                        name=call.function.name,
                        arguments=json.loads(call.function.arguments or "{}"),
                )
                for call in (message.tool_calls or [])
        )
        token_usage = (
                TokenUsage(
                        prompt_tokens=usage.prompt_tokens,
                        completion_tokens=usage.completion_tokens,
                )
                if usage is not None
                else TokenUsage()
        )
        return Completion(
                content=message.content or "",
                tool_calls=tool_calls,
                stop_reason=finish_reason,
                usage=token_usage,
        )


class OpenAIChatModel:
        """Calls OpenAI Chat Completions. Reads ``OPENAI_API_KEY`` from the
        environment when ``api_key`` is not given."""

        def __init__(self, *, model: str, api_key: str | None = None) -> None:
                self._model = model
                self._client = AsyncOpenAI(api_key=api_key)

        def identifier(self) -> str:
                return self._model

        async def complete(
                self,
                conversation: Conversation,
                *,
                tools: Sequence[ToolSchema] | None = None,
        ) -> Completion:
                messages = encode_messages(conversation)
                if tools:
                        response = await self._client.chat.completions.create(
                                model=self._model, messages=messages, tools=encode_tools(tools)
                        )
                else:
                        response = await self._client.chat.completions.create(
                                model=self._model, messages=messages
                        )
                choice = response.choices[0]
                return decode_completion(choice.message, response.usage, choice.finish_reason)
