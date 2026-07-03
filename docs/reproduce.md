# Reproducing the documentation deliverables

This runbook lists the exact steps to regenerate every **generated** deliverable
(the RAG index, the executed-task evidence, the Scribe's per-agent docs, and the
OpenTelemetry trace). The **authored** docs (README, use-case, architecture,
rag-base, reflection) are version-controlled prose and need no regeneration —
they live under `docs/` and are listed at the end.

Run everything from the repository root.

## 0. Prerequisites (once)

```sh
uv sync                          # core install
uv sync --extra observability    # only needed for the Phoenix UI (step 4, optional)
cp .env.sample .env              # then edit .env:
#   OPENAI_API_KEY=...   (required — the runs and embeddings call OpenAI)
#   TAVILY_API_KEY=...   (optional — enables the Researcher's web fallback)
```

A run spends a small amount of API credit (~$0.02 per analysis).

## 1. Build the RAG index

The Researcher retrieves from a persisted vector index built from the FastAPI
corpus (`data/corpus/fastapi/`, 21 docs → ~275 chunks).

```sh
python scripts/ingest_rag.py
# -> indexed <N> chunks from data/corpus/fastapi -> data/rag_index
```

Knobs (optional): `CORPUS_DIR`, `RAG_INDEX_DIR`, `EMBED_MODEL` (see `.env.sample`).

## 2. Executed-task evidence (§8, §9.6)

Two runs over the committed fixture `scripts/sample_app`. The first starts from a
fresh memory; the second reuses it to demonstrate cross-session recall. Both send
the Scribe's output to the evidence folder and capture the console transcript.

```sh
# Task 1 — fresh memory; produces RAG sources, partial-findings, Scribe docs
rm -rf data/memory
DOCS_DIR=docs/evidence/analysis/sample_app MEMORY_DIR=data/memory \
  uv run python scripts/analyze_repo.py > docs/evidence/task-1-analysis.txt 2>&1

# Task 2 — same target, seeded memory; demonstrates memory recall
DOCS_DIR=docs/evidence/analysis/sample_app MEMORY_DIR=data/memory \
  uv run python scripts/analyze_repo.py > docs/evidence/task-2-memory-recall.txt 2>&1
```

This regenerates:

- `docs/evidence/task-1-analysis.txt`, `docs/evidence/task-2-memory-recall.txt` — full transcripts (each ends with an EVIDENCE REPORT: subagents, sources by origin, loop behaviour, tokens/latency/cost, memory recalled/stored, files written).
- `docs/evidence/analysis/sample_app/{explore,research,test}.md` — the Scribe's per-agent documents.

> Note: the transcripts use `.txt`, not `.log` — the repo gitignores `*.log`.
> Results are model-dependent (`gpt-5-nano`): exact numbers (source counts,
> partial-findings) vary run to run; the *shape* of the evidence is stable.

The curated index that maps each §8 demo to its artifact is
[`docs/evidence/task-evidence.md`](evidence/task-evidence.md) (authored; update the
numbers if you re-run).

## 3. OpenTelemetry trace (§9.7)

A durable, headless trace of one run (one span per line):

```sh
OBSERVABILITY=otel-file OTEL_TRACE_FILE=docs/evidence/repo-analysis.otel.jsonl \
  uv run python scripts/analyze_repo.py
```

Regenerates `docs/evidence/repo-analysis.otel.jsonl` (a run root + `llm`/`tool`
spans, per-agent attributed). See [`docs/evidence/README.md`](evidence/README.md).

## 4. Phoenix UI screenshot (§9.7, optional)

Only this deliverable needs a human (headless can't screenshot a UI):

```sh
uv sync --extra observability
OBSERVABILITY=phoenix uv run python scripts/analyze_repo.py
# a local Phoenix UI launches — screenshot the trace view
```

## 5. Verify the codebase

```sh
just validate   # ruff + pyright + pytest (196 tests)
```

## Authored docs (no regeneration)

| Deliverable | File |
| --- | --- |
| README (install/config/run) | [`README.md`](../README.md) |
| Use-case description | [`docs/use-case.md`](use-case.md) |
| Architecture explanation | [`docs/architecture.md`](architecture.md) + [`docs/diagrams/`](diagrams/) |
| RAG base | [`docs/rag-base.md`](rag-base.md) |
| Reflection | [`docs/reflection.md`](reflection.md) |
| Requirements scorecard | [`TP_REQUISITS.md`](../TP_REQUISITS.md) |
