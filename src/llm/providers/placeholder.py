"""A stand-in ChatModel used until a real provider is wired.

It never calls tools and returns a fixed notice, so the CLI and the whole loop
run end-to-end without an API key. Replace it in the composition root (main.py)
with a real ``ChatModel`` to use the agent for actual tasks.
"""

from __future__ import annotations

from collections.abc import Sequence

from llm.messages import Completion, Conversation, ToolSchema


class PlaceholderChatModel:
        async def complete(
                self,
                conversation: Conversation,
                *,
                tools: Sequence[ToolSchema] | None = None,
        ) -> Completion:
                return Completion(
                        content=(
                                "[placeholder model] No LLM provider is configured yet. "
                                "Wire a real ChatModel in main.py to use the agent for real tasks."
                        )
                )
