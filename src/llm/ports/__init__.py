"""Ports (inward-facing abstractions) for the LLM domain."""

from llm.ports.chat_model import ChatModel
from llm.ports.embedding_model import EmbeddingModel

__all__ = ["ChatModel", "EmbeddingModel"]
