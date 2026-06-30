"""Context management: deciding what enters the model's window.

For this increment ``ContextManager`` is a deliberate pass-through: it returns
the conversation unchanged. It exists now as the single seam the reason phase
will consult, so that summarization, windowing, and project-memory injection can
be added later without touching the loop. Splitting it into ``PromptBuilder`` /
``ContextWindow`` / ``Summarizer`` / ``MemoryManager`` is deferred until there is
real context pressure to justify the abstraction.
"""

from __future__ import annotations

from llm import Conversation


class ContextManager:
        """Prepares the conversation handed to the model. Currently identity."""

        def prepare(self, conversation: Conversation) -> Conversation:
                return conversation
