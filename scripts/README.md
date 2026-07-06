# `scripts` — reproducible drivers

Committed entry points that exercise the system end-to-end (the replacements for
ephemeral scratchpad drivers). Run both **from the repository root** so `.env`,
`data/rag_index`, and `data/memory` resolve. Both reuse the model/env/RAG wiring
from [`main.py`](../main.py) rather than duplicating it.

> Full step-by-step regeneration guide: [`docs/reproduce.md`](../docs/reproduce.md).

## `ingest_rag.py` — build the RAG index

```sh
python scripts/ingest_rag.py
```

Reads the framework corpus (`CORPUS_DIR`, default `data/corpus/fastapi`), embeds
it with OpenAI, and writes a persisted vector store (`RAG_INDEX_DIR`, default
`data/rag_index`). Requires `OPENAI_API_KEY`. It is the *only* place that binds
the [`rag`](../src/rag/) pipeline to OpenAI — the pipeline itself is
provider-agnostic. Run it **once** before analyzing (the Researcher's `rag_search`
is enabled only when the index exists).

## `analyze_repo.py` — the use case, with an evidence report

```sh
python scripts/analyze_repo.py [TARGET_DIR]     # TARGET_DIR defaults to scripts/sample_app
```

Runs one repo-analysis task through the principal coordinator against a target
repo, then prints an **evidence report** mapped to the TP's gradable sections:

| Section of the report | What it shows | TP § |
| --- | --- | --- |
| subagents | each subagent's result from the shared ledger | §1/§2 |
| sources by origin | repo / memory / RAG / web / inference counts | §2/§3 |
| control & loop | no-progress nudges, guard stops, partial-findings reports | §4 |
| persistent memory | entries recalled before vs stored after the run | §2/§5 |
| observability | model calls, tools, retrievals, total tokens, estimated cost | §6 |

After the run it also invokes the **Scribe** (via [`Documenter`](../src/agent/documenter.py))
to write one file per agent into `DOCS_DIR` (default `docs/analysis`).

### Capturing a trace

```sh
OBSERVABILITY=phoenix    python scripts/analyze_repo.py    # launches the local Phoenix UI
OBSERVABILITY=otel-file OTEL_TRACE_FILE=trace.jsonl \
                         python scripts/analyze_repo.py    # writes spans as JSONL (headless)
```

## `sample_app/` — the fixture analyzed by default

A small committed FastAPI project used as the default target. It has its own
[README](sample_app/README.md) and is deliberately kept out of the project's lint
(standard 4-space FastAPI code, not project source).
