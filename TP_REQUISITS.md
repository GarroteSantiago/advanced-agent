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
2, and 3 delivered (TDD, atomic commits, 147 tests green, ruff + pyright clean):
- **1a** shared `TaskLedger` on the execution context (`3f7ed66`).
- **1b** enriched observability event stream + opt-in Phoenix adapter
  (`9415564`, `9fde1a4`).
- **2** multi-agent: delegation core + `DelegatingActionPhase` + five concrete
  subagents wired as a principal coordinator (`8b0d5dc`, `4c845aa`, `7bcece0`,
  `bc0e1f7`).
- **3** RAG: chunk/embed/vector/retrieve pipeline + FastAPI corpus + `rag_search`
  wired into the Researcher (`ed87efa`, `8f9472a`, `eafa50b`, `d759fa5`).

**Verification honesty:** the multi-agent flow **and** RAG are now **live-verified**
against real OpenAI (delegation happens; RAG sources reach the ledger). Still
**not** smoke-tested: the Phoenix boundary against a live Phoenix. Deferred
sections (persistent memory, context/loop management, packaged use-case evidence,
deliverable docs) remain open.

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

### Persistent per-project memory — ❌ ABSENT (Phase 5)

- [ ] ❌ Persists across sessions — `src/memory/__init__.py` still a stub.
- [ ] ❌ Stores architecture/files/deps/commands/conventions/decisions/bugs/summaries.

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

## 4. Context handling & agent behavior — mostly ❌ ABSENT (Phase 4)

- [ ] ❌ Strategy for long conversations/tasks — `ContextManager.prepare()` still an identity pass-through, not wired into the reason phase.
- [ ] ❌ Summarizes prior info / preserves decisions.
- [ ] ❌ Avoids sending whole history — full conversation still sent every turn.
- [ ] ❌ **Loop detection** — only a hard iteration cap; `cycle_signature()` hook still unused.
- [ ] ⚠️ On loop: change strategy/replan/stop/ask — only hard-cap → `Halt`.
- [ ] ❌ Insufficient-evidence detection.
- [ ] ❌ When blocked, explain what was tried / what's missing.

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

## 6. Observability — ⚠️ BUILT, not yet exercised live

Phoenix adapter built as an `EventHandler` (`src/observability/`), opt-in via `OBSERVABILITY=phoenix`; Phoenix/OTel in an optional `observability` extra. Event stream enriched.

- [ ] ⚠️ Integrate Langfuse/LangSmith/Phoenix/equivalent — **Phoenix adapter implemented + wired**, but **not smoke-tested against a live Phoenix**.
- [ ] ❌ Used in ≥1 delivered test — no live trace captured yet (pure span-mapping is unit-tested).

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

Unit/integration suite is broad (140 tests). These four are the use-case demos:

- [ ] ⚠️ A task using **RAG** that shows retrieved sources — mechanism live-verified (Researcher retrieved, 35 sources in the ledger); packaged demo/evidence pending.
- [ ] ❌ A task using **project memory**.
- [ ] ❌ A task where the agent **changes strategy / stops / asks for help**.
- [ ] ❌ At least one execution **recorded in the observability tool** (adapter ready; run pending).

---

## 9. Deliverables

- [ ] ⚠️ 1. Complete, working code — harness + multi-agent + observability built & tested; RAG/memory/context still pending.
- [ ] ⚠️ 2. README with install/config/run — needs updating for `OBSERVABILITY`, the `observability` extra, and the multi-agent design.
- [ ] ⚠️ 3. Use-case description — decided (see §7); not yet written up.
- [ ] ⚠️ 4. Architecture explanation — good docstrings + the principal/subagent/ledger design now exists; no deliverable doc yet.
- [ ] ❌ 5. RAG base documentation.
- [ ] ❌ 6. Evidence of ≥2 executed tasks.
- [ ] ❌ 7. Observability screenshots / full trace.
- [ ] ❌ 8. Reflection.

---

## Optional extra

- [ ] ⚠️ **Tool plugin system** — common `Describable`/`ToolInterface` + registry/catalog DONE; auto-discovery (`pkgutil`/`entry_points`) still missing.

---

## Bottom line for planning

| Section | State |
|---|---|
| Base harness, tools, config & policies | ✅ Done and solid |
| Multi-agent architecture (5 subagents) | ✅ Done (fakes-verified; live run pending) |
| Shared task state (TaskLedger) | ✅ Structure + subagent-result merge done; sources/files fill in with §3 |
| Observability (external tool) | ⚠️ Built + opt-in wired; live trace/screenshot pending |
| RAG (chunk/embed/vector/retrieval) | ✅ Done + live-verified (FastAPI corpus; sources reach the ledger) |
| Persistent project memory | ❌ Not started (Phase 5) |
| Context/loop management | ❌ Stubs only (Phase 4) |
| Use case + evidence + deliverable docs | ⚠️ Use case decided; evidence/docs pending |
