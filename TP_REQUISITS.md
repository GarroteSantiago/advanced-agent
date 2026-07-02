# TP Final — Coding Agent Avanzado · Requirements Checklist

Traced from `docs/advanced_ai_agent_tp.pdf`. Each box is a gradable requirement.
Grouped by the spec's own sections so an unchecked box maps directly to what the
evaluators will look for.

---

## Audit status

**Original audit (2026-07-01)** was against `feat/harness-redesign` @ `d1489da`
(now == `main`): a clean, well-tested **single-agent** ReAct harness with real
config-driven guardrails; the advanced layer left as deferred stubs.

**Progress update (2026-07-02) — branch `feat/advanced-layer`.** Phases 1a, 1b,
2, 3, 4, and 5, plus the observability boundary, delivered (TDD, atomic commits,
185 tests green, ruff + pyright clean):
- **1a** shared `TaskLedger` on the execution context (`3f7ed66`).
- **1b** enriched observability event stream + opt-in Phoenix adapter
  (`9415564`, `9fde1a4`).
- **2** multi-agent: delegation core + `DelegatingActionPhase` + five concrete
  subagents wired as a principal coordinator (`8b0d5dc`, `4c845aa`, `7bcece0`,
  `bc0e1f7`).
- **3** RAG: chunk/embed/vector/retrieve pipeline + FastAPI corpus + `rag_search`
  wired into the Researcher (`ed87efa`, `8f9472a`, `eafa50b`, `d759fa5`).
- **4** context & loop management: `ContextManager` windowing, `ProgressTracker`
  nudge-then-stop loop detection, partial-findings synthesis on abort
  (`40589a1`, `6e731d0`, `46600af`, `2b0f6e9`, `97abd65`).
- **obs** event aggregation across subagents + OTel boundary smoke-tested + live
  trace captured (`db971ec`, `cc8a99b`, `fc3561b`, `59c1f05`).
- **5** persistent per-project memory: `ProjectMemory` aggregate + `MemoryStore`
  port + `JsonMemoryStore` + `ProjectMemoryService` run-boundary seam, wired into
  CLI + driver (`2643752`, `75d3a2c`).

**Verification honesty:** the multi-agent flow **and** RAG are now **live-verified**
against real OpenAI (delegation happens; RAG sources reach the ledger); the OTel
boundary is smoke-tested against a real SDK and a live trace is captured
(`docs/evidence/`); persistent per-project memory is live-verified (a second run
over a target is briefed from the first). Only the live **Phoenix UI** screenshot
is still un-captured.
Deferred sections (packaged use-case evidence, deliverable
docs) remain open.

**Legend**
- `[x]` — **DONE**: implemented and covered by tests.
- `[ ]` + ⚠️ **PARTIAL** — foundation/seam exists; noted gap remains.
- `[ ]` + ❌ **ABSENT** — not implemented.

---

## 0. Constraints (hard rules)

- [x] Built on top of the in-class coding agent.
- [x] **No** agent-orchestration frameworks — deps are only `openai` + `tavily-python` (+ optional `arize-phoenix` extra for observability).
- [x] Any language / any LLM API; punctual libs only — compliant.
- [x] Preserve base harness + base tools: read, write, run command, list files, web search — all real.

---

## 1. Agent architecture

- [x] **Main agent**: `Session` receives the task, holds state, owns registry+controller+approver; now the **principal coordinator** (`src/agent/cli.py` `build_session`).
- [x] Main agent may execute tools directly — supported (currently wired tool-less by choice; one line re-enables).
- [x] Each subagent has a clear, single responsibility — five subagents, one role each (`src/agent/team.py`, `src/prompts/__init__.py`).
- [x] Subagents may have **different** tool access and permissions — each runs its own restricted inner loop (`src/agent/subagent.py`).

### Required subagents — ✅ ALL PRESENT (verified with fakes)

Delegation surfaced as tool calls; routed by `DelegatingActionPhase` (`src/harness/loop/phases/delegating_action.py`); reports merged into the shared ledger.

- [x] **Explorer** — `read_file` + `list_files`.
- [x] **Researcher** — `web_search` (RAG retrieval to be added in §3).
- [x] **Implementer** — `read_file` only; **proposes** changes, does not apply (per use-case decision).
- [x] **Tester** — `read_file` + `run_command` (the only command-running subagent).
- [x] **Reviewer** — an **AI** subagent (`read_file`), distinct from the human `PlanReviewer`.

---

## 2. Shared state & memory

### Shared task state — ✅ mostly DONE

`TaskLedger` (`src/harness/runtime/ledger.py`) is an immutable, copy-on-write value object held by `AgentExecutionContext` and **shared with subagents** via report-merge; exposed on `ExecutionResult.ledger`.

- [x] A shared task-state structure exists **and is shared** with subagents (merge on delegation).
- [x] Records the **original request** — seeded via `for_task(..., request=)`.
- [ ] ⚠️ Records **progress** — `progress` field + `noting_progress` transition exist; iteration/token counters live; not yet auto-populated with milestone steps.
- [x] Records **subagent results** — merged by `DelegatingActionPhase` (`crediting`).
- [x] Records **sources consulted** — populated live: RAG retrievals flow in as `Origin.RAG` (verified: 35 sources reached the ledger in a live run). Repo/web reads not yet auto-tagged.
- [ ] ⚠️ Records **modified files** — `modified_files` field + `touching` transition exist; **populated once the write-path→ledger wiring lands**.
- [ ] ⚠️ Records **relevant observations** — `observations` field + `observing_that` transition exist; auto-population partial.

### Persistent per-project memory — ✅ DONE (Phase 5, live-verified)

`src/memory/`: `ProjectMemory` aggregate (immutable, copy-on-write, self-briefing) over the spec's category buckets; `MemoryStore` port + `JsonMemoryStore` (one JSON per project under gitignored `data/memory/`); `ProjectMemoryService` briefs a run at start and absorbs its ledger at end. Wired into both the CLI (keyed by working dir) and the `analyze_repo` driver (keyed by target path). Injected as a seeded briefing at the run boundary, **not** through `ContextManager` (kept a pure windowing projection).

- [x] ✅ Persists across sessions — live-verified: a first run of `scripts/sample_app` stored 5 entries; a fresh process re-run recalled all 5 to brief the agent (grew to 9).
- [ ] ⚠️ Stores architecture/files/deps/commands/conventions/decisions/bugs/summaries — the 8 category buckets exist; deterministic ledger-based capture currently fills the coarse **summaries** + **files** buckets. Sorting learnings into the finer buckets is the noted model-**digest** seam (`ProjectMemoryService.absorb`).

---

## 3. RAG & information retrieval — ✅ DONE (live-verified)

Framework-level corpus, **FastAPI** (21 curated docs → 275 chunks). Embeddings: OpenAI `text-embedding-3-small`; store: in-house numpy (`src/rag/`). Wired into the Researcher via `rag_search` (`src/agent/rag_tool.py`).

- [x] Agent specialized in a chosen ecosystem — FastAPI corpus.
- [x] RAG over docs/examples/READMEs — `ingest_corpus` over the docs corpus.
- [x] Chunking — `rag.Chunker`.
- [x] Embeddings — `EmbeddingModel` port + `OpenAIEmbeddingModel`.
- [x] Vector storage — `VectorStore` port + `NumpyVectorStore` (cosine + disk persistence).
- [x] Retrieve relevant context before answering — `Retriever`; Researcher retrieves before summarizing.
- [x] Show which docs/fragments were retrieved & used — fragments returned in the tool result + `DocumentsRetrieved` event.
- [ ] ⚠️ Differentiate source: repo vs memory vs RAG vs web vs inference — `Origin` tag exists; **RAG emits `Origin.RAG`** (live); repo/web reads not yet auto-tagged.
- [x] RAG-first, web-fallback ordering — Researcher prompt + tool order.

---

## 4. Context handling & agent behavior — ✅ DONE (Phase 4)

- [x] Strategy for long conversations/tasks — `ContextManager.prepare()` is wired into the reason phase (`src/harness/loop/phases/reason.py`) as a read-time projection.
- [ ] ⚠️ Summarizes prior info / preserves decisions — **structural** windowing (leading instructions + original task + recent turns kept, middle elided behind a marker); durable decisions live in the `TaskLedger`. Semantic (model-based) summary via a `Summarizer` port is the noted next seam.
- [x] Avoids sending whole history — `ContextManager` windows above `max_messages`; the elision boundary never orphans a tool result.
- [x] **Loop detection** — `ProgressTracker` (`src/harness/control/progress_tracker.py`) over the now-recorded `cycle_signature()` history.
- [x] On loop: change strategy/replan/stop/ask — **nudge-then-stop**: first repeat folds corrective guidance into the conversation (`StrategyNudged`) and continues; a further repeat aborts.
- [ ] ⚠️ Insufficient-evidence detection — no *proactive* detector; the closest behavior is the partial-findings synthesis on abort (below).
- [x] When blocked, explain what was tried / what's missing — `PartialSynthesizer` (`src/agent/synthesis.py`) runs a forced recap turn so a capped/stalled subagent reports findings + blockers, tagged partial.

---

## 5. Config file & agent policies — ✅ DONE

- [x] Reads a config file — `PolicyConfig.from_toml` via stdlib `tomllib`.
- [x] Config **validated before every tool call** — `PolicyVerifier.review` before `tool.invoke`, fail-closed.
- [x] **Read** deny list.
- [x] **Write** deny list.
- [x] **Command** deny list.
- [x] **Approval-required** commands.
- [x] *(bonus)* Workspace confinement.

---

## 6. Observability — ✅ event stream aggregated LIVE; OTel boundary smoke-tested + live trace captured

Phoenix adapter built as an `EventHandler` (`src/observability/`), opt-in via `OBSERVABILITY=phoenix`; Phoenix/OTel in an optional `observability` extra. Event stream enriched **and aggregated across the whole team**: subagents run on their own buses, and an `EventForwarder` bridges each onto the principal bus (tagged with `Event.source`), so a single sink sees the full run. The `PhoenixTracer` maps that stream onto nested OTel spans — one run root, an `llm` span per model call, a `tool` span per tool call — and is now smoke-tested against a **real OTel SDK** (`test_observability_phoenix.py`, in-memory exporter), including the single-root invariant (a subagent's forwarded stop must not close the principal's root). A live analysis of `scripts/sample_app` was recorded to an OTel trace: **59 spans in one run tree** (27 llm, 31 tool, 1 root), every span attributed to its agent (`principal`/`explore`/`research`/`test`) via `Event.source` — captured at `docs/evidence/repo-analysis.otel.jsonl` by the `OBSERVABILITY=otel-file` sink. The only remaining gap is a screenshot of the **live Phoenix UI** (the `OBSERVABILITY=phoenix` path); the durable file trace is the headless equivalent.

- [x] ✅ Integrate Langfuse/LangSmith/Phoenix/equivalent — **Phoenix/OTel adapter implemented, wired, and smoke-tested against a real OTel SDK**. Live Phoenix-UI screenshot still optional.
- [x] ✅ Used in ≥1 delivered test — live trace captured (`docs/evidence/`) **and** the boundary exercised in a delivered test (`test_observability_phoenix.py`).

### Minimum recorded fields (event stream, `src/harness/events/event.py`)

- [ ] ⚠️ Prompts — message *count* captured; prompt content not yet.
- [x] Model used — `ModelCalled.model` / `ModelCompleted.model`.
- [x] LLM calls — `ModelCalled` + `ModelCompleted`.
- [x] Tools invoked — `ToolInvoked` (with arguments).
- [x] Documents retrieved — `DocumentsRetrieved(query, sources)` emitted by `rag_search`.
- [ ] ⚠️ Web searches — surface as generic `ToolInvoked(web_search)`.
- [x] Iterations — `CycleCompleted.iteration`.
- [x] Errors — `ToolObserved.error` + `GuardTripped.reason`.
- [x] Latency — `ModelCompleted.latency_ms`.
- [x] Tokens — `ModelCompleted.prompt_tokens/completion_tokens`.
- [x] Estimated cost — `ModelCompleted.cost_usd` via `src/llm/pricing.py`.
- [x] Final result — `LoopStopped.output` (+ `ExecutionResult`).

---

## 7. Concrete use case — ⚠️ DECIDED, not yet executed

- [ ] ⚠️ Define a concrete objective over a chosen repo/ecosystem — **decided**: analyze an unknown FastAPI repo → architecture/deps/risks/commands report. Exercised in live smoke runs; not yet a packaged deliverable.
- [ ] ⚠️ Verifiable result produced — live runs produced coherent reports; formal success-criterion write-up pending.
- [x] Fits a use-case shape — repo-analysis report.

---

## 8. Tests to run with the agent — ❌ ABSENT (as end-to-end demos)

Unit/integration suite is broad (185 tests). These four are the use-case demos:

- [ ] ⚠️ A task using **RAG** that shows retrieved sources — mechanism live-verified (Researcher retrieved, 35 sources in the ledger); packaged demo/evidence pending.
- [x] ⚠️ A task using **project memory** — mechanism live-verified end-to-end (a second run of `scripts/sample_app` was briefed from the first via `data/memory/`); packaging this two-run demo as committed evidence is still pending.
- [ ] ⚠️ A task where the agent **changes strategy / stops / asks for help** — mechanism now exists (nudge-then-stop + partial-findings synthesis, Phase 4); packaged end-to-end demo/evidence still pending.
- [x] ✅ At least one execution **recorded in the observability tool** — live OTel trace of a full run at `docs/evidence/repo-analysis.otel.jsonl` (59 spans, single-rooted, per-agent attributed).

---

## 9. Deliverables

- [ ] ⚠️ 1. Complete, working code — harness + multi-agent + observability built & tested; RAG/memory/context still pending.
- [ ] ⚠️ 2. README with install/config/run — needs updating for `OBSERVABILITY`, the `observability` extra, and the multi-agent design.
- [ ] ⚠️ 3. Use-case description — decided (see §7); not yet written up.
- [ ] ⚠️ 4. Architecture explanation — good docstrings + the principal/subagent/ledger design now exists; no deliverable doc yet.
- [ ] ❌ 5. RAG base documentation.
- [ ] ❌ 6. Evidence of ≥2 executed tasks.
- [ ] ⚠️ 7. Observability screenshots / full trace — **full OTel trace captured** (`docs/evidence/`); live Phoenix-UI screenshot still optional.
- [ ] ❌ 8. Reflection.

---

## Optional extra

- [ ] ⚠️ **Tool plugin system** — common `Describable`/`ToolInterface` + registry/catalog DONE; auto-discovery (`pkgutil`/`entry_points`) still missing.

---

## Bottom line for planning

| Section | State |
|---|---|
| Base harness, tools, config & policies | ✅ Done and solid |
| Multi-agent architecture (5 subagents) | ✅ Done + live-verified (real gpt-5-nano delegates; reports merge into the ledger) |
| Shared task state (TaskLedger) | ✅ Structure + subagent-result merge done; sources/files fill in with §3 |
| Observability (external tool) | ✅ Built + wired + OTel boundary smoke-tested; live trace captured (`docs/evidence/`). Phoenix-UI screenshot optional |
| RAG (chunk/embed/vector/retrieval) | ✅ Done + live-verified (FastAPI corpus; sources reach the ledger) |
| Persistent project memory | ✅ Done (Phase 5): ProjectMemory + JSON store + run-boundary service; live-verified cross-session recall |
| Context/loop management | ✅ Done (Phase 4): windowing wired, no-progress detection (nudge-then-stop), partial-findings on abort |
| Use case + evidence + deliverable docs | ⚠️ Use case decided; evidence/docs pending |
