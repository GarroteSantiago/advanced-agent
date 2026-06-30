"""LLM domain: conversation value objects and the model port.

Adapters to concrete providers live in ``llm.providers`` (a deferred seam).
"""

from llm.messages import (
        Completion,
        Conversation,
        Message,
        Role,
        TokenUsage,
        ToolCall,
        ToolSchema,
)
from llm.ports import ChatModel

__all__ = [
        "ChatModel",
        "Completion",
        "Conversation",
        "Message",
        "Role",
        "TokenUsage",
        "ToolCall",
        "ToolSchema",
]
