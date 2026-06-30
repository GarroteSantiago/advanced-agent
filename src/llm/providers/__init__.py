"""LLM provider adapters (outer ring).

``OpenAIChatModel`` is the real provider; ``PlaceholderChatModel`` is the
keyless stand-in used when no provider is configured.
"""

from llm.providers.openai_model import OpenAIChatModel
from llm.providers.placeholder import PlaceholderChatModel

__all__ = ["OpenAIChatModel", "PlaceholderChatModel"]
