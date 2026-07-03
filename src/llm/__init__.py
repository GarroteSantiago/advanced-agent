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
from llm.ports import ChatModel, EmbeddingModel
from llm.pricing import estimate_cost

__all__ = [
        "ChatModel",
        "Completion",
        "Conversation",
        "EmbeddingModel",
        "Message",
        "Role",
        "TokenUsage",
        "ToolCall",
        "ToolSchema",
        "estimate_cost",
]
