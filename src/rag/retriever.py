"""Retrieval and indexing: the two ends of the RAG pipeline.

``Indexer`` builds the store (chunk -> embed -> add); ``Retriever`` answers a
query (embed -> nearest chunks). Both depend only on the ``EmbeddingModel`` and
``VectorStore`` ports, so the pipeline is provider-agnostic and testable with a
fake embedder.
"""

from __future__ import annotations

from collections.abc import Iterable

from llm import EmbeddingModel
from rag.chunk import Chunker
from rag.store import Retrieved, VectorStore

_BATCH = 128


class Retriever:
        """Embeds a query and returns the most similar chunks."""

        def __init__(self, embedder: EmbeddingModel, store: VectorStore) -> None:
                self._embedder = embedder
                self._store = store

        async def retrieve(self, query: str, k: int = 4) -> list[Retrieved]:
                vectors = await self._embedder.embed([query])
                if not vectors:
                        return []
                return self._store.search(vectors[0], k)


class Indexer:
        """Chunks documents, embeds them in batches, and fills the store."""

        def __init__(
                self, embedder: EmbeddingModel, store: VectorStore, chunker: Chunker | None = None
        ) -> None:
                self._embedder = embedder
                self._store = store
                self._chunker = chunker or Chunker()

        async def index(self, documents: Iterable[tuple[str, str]]) -> int:
                chunks = [
                        chunk
                        for source, text in documents
                        for chunk in self._chunker.chunk(text, source)
                ]
                for start in range(0, len(chunks), _BATCH):
                        batch = chunks[start : start + _BATCH]
                        embeddings = await self._embedder.embed([chunk.text for chunk in batch])
                        self._store.add(embeddings, batch)
                return len(chunks)
