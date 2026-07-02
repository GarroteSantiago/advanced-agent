# Evidence — executed-task demos (§8, §9.6)

Two live executions of the repo-analysis agent (real `gpt-5-nano`) over the
committed fixture `scripts/sample_app`, captured here as durable artifacts. Each
run drives the principal coordinator + its five analysis subagents, then the
run-boundary Scribe writes the findings into this folder. Reproduce with:

```
DOCS_DIR=docs/evidence/analysis/sample_app MEMORY_DIR=data/memory \
  uv run python scripts/analyze_repo.py
```

(Requires `OPENAI_API_KEY` in `.env`; the RAG index at `data/rag_index`.)

## The four §8 demos → where to see each

| §8 requirement | Demonstrated by | Artifact |
|---|---|---|
| A task using **RAG** that shows retrieved sources | Run 1 consulted **44** RAG sources; the Researcher's output cites FastAPI conventions | `task-1-analysis.txt` (`sources consulted … rag: 44`), `analysis/sample_app/research.md` |
| A task using **project memory** (persists across sessions) | Run 1 stored 7 entries (first run); **Run 2 recalled all 7** and was briefed from them (grew to 11) | `task-1-analysis.txt` (`recalled … 0`), `task-2-memory-recall.txt` (`recalled … 7 entries`) |
| A task where the agent **changes strategy / stops / explains what's missing** | Subagents that hit the iteration cap stop gracefully and return **partial findings** (what they found + why partial), not a bare halt reason — **4 partial-findings reports** in Run 1 | `task-1-analysis.txt` (`partial-findings reports: 4`, `[partial -- iteration-limiter …]` entries) |
| At least one execution **recorded in the observability tool** | Full OpenTelemetry trace of a run: 59 spans, single-rooted, per-agent attributed | `repo-analysis.otel.jsonl` (+ `README.md`) |

## Written results (the Scribe, §1/§2)

The Scribe — the only agent with write permission, confined to this folder by a
per-agent policy — documented each contributing agent's findings, one file per
agent (`analysis/sample_app/{explore,research,test}.md`). Only the three agents
the principal actually delegated to were documented, as intended.

## Run summaries

**Run 1** (`task-1-analysis.txt`) — fresh memory:
- succeeded; 47 model calls; 123k tokens; ~$0.018 across principal + subagents.
- RAG: 44 sources · partial-findings: 4 · guard stops: 4 (iteration cap) · nudges: 0 (no real loop occurred — correctly quiescent).
- Scribe wrote `explore.md`, `research.md`, `test.md`.

**Run 2** (`task-2-memory-recall.txt`) — same target, seeded memory:
- **recalled 7 entries** before the run (briefed from Run 1), stored 11 after.
- Scribe re-documented the three agents' findings.
