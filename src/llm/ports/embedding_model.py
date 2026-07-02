"""The embedding model port.

``EmbeddingModel`` is the abstraction the RAG layer depends on to turn text into
vectors. Like ``ChatModel`` it is a structural port; concrete providers live
outward in ``llm.providers``. It is batch-oriented (``embed`` takes many texts)
so ingestion can embed a whole chunk set in as few provider calls as possible.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable


@runtime_checkable
class EmbeddingModel(Protocol):
        """Turns texts into fixed-length embedding vectors."""

        def identifier(self) -> str:
                """The model's own name (e.g. ``text-embedding-3-small``)."""
                ...

        async def embed(self, texts: Sequence[str]) -> list[list[float]]: ...
