"""Vector storage: the retrieval index behind a port.

``VectorStore`` is the seam the retriever depends on; ``NumpyVectorStore`` is an
in-house adapter that keeps normalized embeddings in a numpy matrix and does
cosine similarity by a single matrix-vector product. It persists to disk so the
corpus is embedded once (ingest) and reused across runs. Swap the adapter (chroma,
faiss, ...) without touching the retriever.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

import numpy as np

from rag.chunk import Chunk


@dataclass(frozen=True, slots=True)
class Retrieved:
        """A chunk returned by a search, with its similarity score."""

        score: float
        chunk: Chunk


@runtime_checkable
class VectorStore(Protocol):
        """An index of embedded chunks that answers nearest-neighbour queries."""

        def add(self, embeddings: Sequence[Sequence[float]], chunks: Sequence[Chunk]) -> None: ...

        def search(self, query: Sequence[float], k: int) -> list[Retrieved]: ...

        def __len__(self) -> int: ...


def _normalize(matrix: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return matrix / norms


class NumpyVectorStore:
        """In-memory cosine-similarity store over a numpy matrix."""

        def __init__(self) -> None:
                self._matrix: np.ndarray | None = None
                self._chunks: list[Chunk] = []

        def add(self, embeddings: Sequence[Sequence[float]], chunks: Sequence[Chunk]) -> None:
                if len(embeddings) != len(chunks):
                        raise ValueError("embeddings and chunks must be the same length")
                if not embeddings:
                        return
                block = _normalize(np.asarray(embeddings, dtype=np.float32))
                self._matrix = block if self._matrix is None else np.vstack([self._matrix, block])
                self._chunks.extend(chunks)

        def search(self, query: Sequence[float], k: int) -> list[Retrieved]:
                if self._matrix is None or k <= 0:
                        return []
                vector = _normalize(np.asarray([query], dtype=np.float32))[0]
                scores = self._matrix @ vector
                top = np.argsort(scores)[::-1][:k]
                return [Retrieved(score=float(scores[i]), chunk=self._chunks[i]) for i in top]

        def __len__(self) -> int:
                return len(self._chunks)

        def save(self, directory: Path) -> None:
                directory.mkdir(parents=True, exist_ok=True)
                matrix = self._matrix if self._matrix is not None else np.empty((0, 0), np.float32)
                np.save(directory / "embeddings.npy", matrix)
                payload = [
                        {"text": c.text, "source": c.source, "ordinal": c.ordinal}
                        for c in self._chunks
                ]
                (directory / "chunks.json").write_text(json.dumps(payload), encoding="utf-8")

        @classmethod
        def load(cls, directory: Path) -> NumpyVectorStore:
                store = cls()
                matrix = np.load(directory / "embeddings.npy")
                store._matrix = matrix if matrix.size else None
                payload = json.loads((directory / "chunks.json").read_text(encoding="utf-8"))
                store._chunks = [
                        Chunk(text=item["text"], source=item["source"], ordinal=item["ordinal"])
                        for item in payload
                ]
                return store
