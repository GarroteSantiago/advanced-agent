"""Build the RAG index from the FastAPI corpus (reproducible ingest).

Reads the framework docs under ``data/corpus/fastapi`` (or ``CORPUS_DIR``),
embeds them with OpenAI, and writes a persisted vector store to
``data/rag_index`` (or ``RAG_INDEX_DIR``). Run from the repository root; requires
``OPENAI_API_KEY`` in ``.env`` (embedding spends a small amount of API credit).

    python scripts/ingest_rag.py

The embedder is injected into ``rag.ingest_corpus``, so this script is the only
place that binds the pipeline to OpenAI; the pipeline itself is provider-agnostic.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import main  # noqa: E402
from llm.providers import OpenAIEmbeddingModel  # noqa: E402
from rag import ingest_corpus  # noqa: E402


async def _run() -> None:
        main._load_dotenv()
        if not os.environ.get("OPENAI_API_KEY"):
                raise SystemExit("OPENAI_API_KEY is required to embed the corpus (set it in .env).")

        corpus = Path(os.environ.get("CORPUS_DIR", "data/corpus/fastapi"))
        out_dir = Path(os.environ.get("RAG_INDEX_DIR", "data/rag_index"))
        if not corpus.is_dir():
                raise SystemExit(f"corpus directory not found: {corpus}")

        embedder = OpenAIEmbeddingModel(model=os.environ.get("EMBED_MODEL", "text-embedding-3-small"))
        count = await ingest_corpus(corpus, out_dir, embedder)
        print(f"indexed {count} chunks from {corpus} -> {out_dir}")


if __name__ == "__main__":
        asyncio.run(_run())
