"""Corpus ingestion: build a persisted vector index from local documents.

Reads text/markdown files from a directory, runs them through the Indexer
(chunk -> embed -> store), and saves the store to disk so retrieval reuses the
embeddings across runs. The embedder is injected, so ingestion is provider- and
network-agnostic (the caller passes OpenAI or a fake).
"""

from __future__ import annotations

from pathlib import Path

from llm import EmbeddingModel
from rag.chunk import Chunker
from rag.retriever import Indexer
from rag.store import NumpyVectorStore

_SUFFIXES = (".md", ".markdown", ".txt", ".rst")


def gather_documents(corpus: Path) -> list[tuple[str, str]]:
        """Read every supported file under ``corpus`` as (relative-source, text)."""
        documents: list[tuple[str, str]] = []
        for path in sorted(corpus.rglob("*")):
                if path.is_file() and path.suffix.lower() in _SUFFIXES:
                        documents.append((str(path.relative_to(corpus)), path.read_text(encoding="utf-8")))
        return documents


async def ingest_corpus(
        corpus: Path,
        out_dir: Path,
        embedder: EmbeddingModel,
        chunker: Chunker | None = None,
) -> int:
        """Ingest ``corpus`` into a fresh store saved at ``out_dir``; return chunk count."""
        documents = gather_documents(corpus)
        store = NumpyVectorStore()
        count = await Indexer(embedder, store, chunker).index(documents)
        store.save(out_dir)
        return count
