# RAG base

The Researcher subagent answers framework questions from a **retrieval-augmented**
knowledge base rather than the model's parametric memory. This document describes
the corpus, the pipeline, and how to rebuild the index.

## Corpus — framework-level, FastAPI

- **Location:** `data/corpus/fastapi/` (21 curated Markdown documents; gitignored).
- **Contents:** FastAPI's own docs — routing/`APIRouter`, bigger-applications
  structure, dependencies, request bodies, background tasks, lifespan, CORS,
  testing, async, etc.
- **Scope decision:** *framework-level*, not language-level. A focused corpus
  gives high retrieval precision without the metadata-filtering / re-ranking
  machinery a broad corpus needs. Specialized knowledge, general targets: the
  agent can analyze *any* unknown FastAPI repo against this one corpus.

## Pipeline (`src/rag/`)

```
documents ─▶ Chunker ─▶ EmbeddingModel ─▶ VectorStore ─▶ Retriever
             (chunk)     (embed, port)     (cosine, disk)  (top-k)
```

- **`Chunker`** — splits each document into overlapping text chunks
  (`Chunk(text, source, ordinal)`), preserving the source path for attribution.
- **`EmbeddingModel`** (port) — `OpenAIEmbeddingModel` adapter uses
  `text-embedding-3-small` by default (`EMBED_MODEL`). The port keeps the pipeline
  provider-agnostic; ingestion and tests inject a fake.
- **`NumpyVectorStore`** — an in-house cosine-similarity store (numpy) that
  persists to disk (`embeddings.npy` + `chunks.json`), so embeddings are computed
  once and reused across runs. No external vector DB — punctual libraries only.
- **`Retriever` / `Indexer`** — `Indexer` builds the store (chunk → embed → save);
  `Retriever` embeds a query and returns the top-k `Retrieved(score, chunk)`.

The build over the FastAPI corpus produces **~275 chunks**.

## Retrieval at query time

The Researcher is wired **RAG-first, web-fallback**: it calls `rag_search`
(`src/agent/rag_tool.py`) before `web_search`. Each `rag_search`:

1. returns the retrieved fragments to the model (so it reasons over real text),
2. emits a `DocumentsRetrieved(query, sources)` event (observability), and
3. logs each hit as a `Source(Origin.RAG)` into a `RetrievalLog` that drains into
   the subagent's report — so **retrieved sources reach the shared ledger** and
   are distinguishable from repo reads, web results, or inference (`Origin`).

## Building / rebuilding the index

```sh
# needs OPENAI_API_KEY in .env (embedding spends a little API credit)
python scripts/ingest_rag.py
```

Environment knobs (see `.env.sample`): `CORPUS_DIR` (default
`data/corpus/fastapi`), `RAG_INDEX_DIR` (default `data/rag_index`), `EMBED_MODEL`.
The `analyze_repo` driver and the CLI load the index from `RAG_INDEX_DIR` when it
exists; without it, the Researcher falls back to web search only.

## Evidence

A live run consulted **44 RAG sources** and the Researcher's `research.md`
document cites FastAPI conventions — see
[`evidence/task-evidence.md`](evidence/task-evidence.md).
