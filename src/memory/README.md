# `memory` — persistent per-project memory

Durable knowledge about a **specific target project** that survives across agent
sessions. Three distinct notions of "state" in this system, kept separate on
purpose:

| | Scope | Lifetime | Package |
| --- | --- | --- | --- |
| `TaskLedger` | one run | discarded when the run ends | [`harness/runtime`](../harness/runtime/) |
| `ProjectMemory` | one project | persisted across sessions | **here** |
| RAG corpus | a framework | rebuilt from source docs | [`rag`](../rag/) |

> Diagram: [`memory.puml`](memory.puml). Up one level: [`../README.md`](../README.md).

## Key objects

| Type | File | Role |
| --- | --- | --- |
| `ProjectMemory` | [`project_memory.py`](project_memory.py) | The aggregate — immutable, copy-on-write, **not anemic**: it renders itself as a `brief()` for injection into a later run. `remember(category, content)` suppresses exact duplicates; empty memory briefs as `""`. |
| `MemoryCategory` | [`project_memory.py`](project_memory.py) | The spec's mandated buckets: `ARCHITECTURE/FILE/DEPENDENCY/COMMAND/CONVENTION/DECISION/BUG/SUMMARY`. Their order defines briefing order. |
| `MemoryEntry` | [`project_memory.py`](project_memory.py) | One `(category, content)` fact. |
| `MemoryStore` | [`store.py`](store.py) | Port: `load(project_id)` / `save(project_id, memory)`. Loading an unknown project yields **empty** memory, so callers never special-case "first run". |
| `JsonMemoryStore` | [`store.py`](store.py) | Filesystem adapter: one JSON file per project (id slugified). Rehydrates through the aggregate's own `remember`, so the domain stays the single arbiter of validity; malformed records are skipped, not fatal. |
| `ProjectMemoryService` | [`service.py`](service.py) | The **run-boundary seam**: `briefing(project_id)` before a run, `absorb(project_id, result)` after. The *only* place that knows both an `ExecutionResult` and the store. |

## Why the service sits at the boundary

Keeping capture at the run boundary is *why* [`ContextManager`](../harness/context/)
can stay a pure, stateless windowing projection — memory is injected **once** as a
briefing, not re-derived every reason turn. Capture is deterministic and
model-free today: subagent summaries + final report → `SUMMARY`, touched files →
`FILE`. A model-based *digest* that sorts learnings into the finer buckets is the
noted next seam (mirroring the `Summarizer` seam in `ContextManager`).

## Collaborators

Depends inward on [`harness.runtime`](../harness/runtime/) (`ExecutionResult`,
`TaskLedger`). Wired in [`main.py`](../../main.py): brief the principal's prompt
before the run, absorb via the `on_result` hook after each turn.
