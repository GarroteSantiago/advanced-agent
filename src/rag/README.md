# `rag` — chunk, embed, store, retrieve

Retrieval-augmented generation over a **framework-level** corpus (general
knowledge, e.g. FastAPI docs) — distinct from [`memory`](../memory/) (durable
knowledge about a *specific* project) and the in-run `TaskLedger`. The whole
pipeline depends only on the [`EmbeddingModel`](../llm/) and `VectorStore` ports,
so it is provider-agnostic and testable with a fake embedder.

> Diagram: [`rag.puml`](rag.puml). Corpus + build guide:
> [`docs/rag-base.md`](../../docs/rag-base.md). Up one level: [`../README.md`](../README.md).

## Pipeline

```
documents ──Chunker──> Chunk[] ──EmbeddingModel──> vectors ──VectorStore.add──> index (persisted)
query ─────────────────────────EmbeddingModel──> vector ──VectorStore.search──> Retrieved[] (score+chunk)
```

## Key objects

| Type | File | Role |
| --- | --- | --- |
| `Chunk` | [`chunk.py`](chunk.py) | One retrievable passage + its `source` and `ordinal`. Carrying `source` is what lets a retrieval be *attributed* (spec's "show which fragments"). |
| `Chunker` | [`chunk.py`](chunk.py) | Pure (no embed/IO): splits text into overlapping character windows (`size=900`, `overlap=150`), dropping a trailing window subsumed by the previous. |
| `VectorStore` | [`store.py`](store.py) | Port: `add`, `search(query, k)`, `__len__`. |
| `NumpyVectorStore` | [`store.py`](store.py) | In-house adapter: normalized embeddings in a numpy matrix; cosine similarity is one matrix-vector product. `save`/`load` persist to disk (`embeddings.npy` + `chunks.json`) so the corpus is embedded **once**. Swap for chroma/faiss without touching the retriever. |
| `Retrieved` | [`store.py`](store.py) | A search hit: `score` + `chunk`. |
| `Retriever` | [`retriever.py`](retriever.py) | `retrieve(query, k=4)`: embed the query, return nearest chunks. |
| `Indexer` | [`retriever.py`](retriever.py) | `index(documents)`: chunk → embed in batches of 128 → fill the store; returns chunk count. |
| `gather_documents` / `ingest_corpus` | [`ingest.py`](ingest.py) | Read `.md/.markdown/.txt/.rst` under a corpus dir, index them, save the store. Embedder injected, so ingestion is network-agnostic. |

## How retrieved provenance reaches the ledger

The Researcher's `RagSearchTool` (in [`agent/`](../agent/), because it bridges
`rag` ↔ harness) records each hit as a `Source(Origin.RAG)` and emits a
`DocumentsRetrieved` event, so retrieved sources drain into the subagent's report
and then the shared ledger.

## Collaborators

Depends inward on [`llm`](../llm/) (`EmbeddingModel`). Consumed by
[`agent`](../agent/) (the RAG tool, wired in [`main.py`](../../main.py)) and the
[`scripts/ingest_rag.py`](../../scripts/) driver.
