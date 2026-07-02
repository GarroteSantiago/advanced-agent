# Architecture

The advanced-agent is a coding-agent **harness** with a multi-agent layer, RAG,
persistent memory, and observability — built **without any orchestration
framework** (no LangChain/LangGraph). The dependencies are `openai` +
`tavily-python`, plus an optional `arize-phoenix` extra. Everything else is
in-house and organized as an **onion**: pure domain at the center, I/O adapters
at the edge, ports pointing inward.

The PlantUML diagrams in [`diagrams/`](diagrams/) show the object graph, the
runtime collaboration, and one ReAct turn step-by-step. This document explains
the *why*.

## Layers (onion)

```
llm  ─ message value objects + the ChatModel/EmbeddingModel ports
harness/
  runtime  ─ AgentExecutionContext (immutable spine) + TaskLedger (shared state)
  loop     ─ Phase + Outcome + Navigator (transition table) + AgentLoop
  tools    ─ ToolInterface, ToolExecutor, registry/catalog, Approver + policy
  control  ─ Guard/Controller, ProgressTracker
  context  ─ ContextManager (windowing projection)
  events   ─ Event/EventBus/handlers, EventForwarder
  delegation ─ Delegate port, SubagentRegistry, SubagentReport
agent/   ─ Session, Subagent, team, Documenter, RAG tool, planning, progress, CLI
rag/     ─ Chunker, EmbeddingModel port, VectorStore, Retriever, Indexer, ingest
memory/  ─ ProjectMemory, MemoryStore + JsonMemoryStore, ProjectMemoryService
observability/ ─ pure span mapping + the Phoenix/OTel boundary
prompts/ ─ role prompts (wording kept out of behavior)
```

Rule of dependency: inner rings never import outer ones. Ports (`ChatModel`,
`ToolInterface`, `Approver`, `MemoryStore`, `Renderer`/`Inputer`) are defined
inward; adapters (OpenAI, the five tools, the JSON store, console I/O) live
outward and are wired in `main.py` / `agent/cli.py`.

## The loop is a dumb driver

An `AgentLoop` runs a **phase**, then asks a **`Navigator`** what to do next. The
navigator consults a static transition table and returns a sum type,
`Continue(nextPhase) | Halt` — never `None`. This sum type was chosen over a
boolean/`None` because it extends cleanly to a third case (`AwaitInput`, for
"ask for help") that a boolean cannot express.

The three phases are the ReAct cycle:

- **ReasonPhase** asks the `ChatModel` what to do (answer, or request tools).
- **ActionPhase** runs the requested tool calls through the `ToolExecutor`.
- **ObservationPhase** folds results back in and asks the control layer whether
  to continue.

Each phase returns `PhaseResult(context, Outcome)`; the loop matches the outcome
against the table. Swapping the loop (e.g. per subagent) happens at one seam.

## Immutable spine + shared ledger

`AgentExecutionContext` is a frozen dataclass threaded through every phase. Each
transition (`with_assistant`, `observed`, `stopped`, `touching_all`, …) returns a
**new** context, so a phase can never corrupt state for another and internal
lists are never exposed mutably. One iteration == one model call (incremented in
`with_assistant`), which is what the `IterationLimiter` caps.

The context holds a **`TaskLedger`** — the spec's "shared task state": the
original request, progress, each subagent's result, sources consulted (tagged by
`Origin`: repo/memory/RAG/web/inference), modified files, and observations. It is
copy-on-write too, which is exactly what lets the principal and its subagents
share one ledger safely: merging a subagent's report never mutates a ledger
someone else is reading.

## Multi-agent delegation

The principal is a tool-less **coordinator**. Subagents are exposed to it as
*tools* via a `Describable` protocol, so the same `ToolCatalog` renders either.
A `DelegatingActionPhase` routes a subagent call to the `SubagentRegistry`,
`await`s the subagent's own inner `AgentLoop`, and **merges** the returned
`SubagentReport` (result, sources, modified files, observations) into the shared
ledger. Delegation cannot recurse: subagents run the plain `ActionPhase`.

Each `Subagent` is a constrained agent — its own restricted tool set, role
prompt, approver, and iteration cap — the concrete realization of "different
tools/permissions per subagent."

### Partial findings on abort

A subagent that hits its iteration cap does **not** hand back a bare halt reason.
A `PartialSynthesizer` runs one forced, tool-less recap turn over the aborted
conversation, so the report is `[partial -- <reason>] <what it found>`. This is
the "when blocked, explain what was tried and what's missing" behavior.

## Control: hard limits and soft stalls

`ObservationPhase` consults two collaborators in order of severity. The
**`Controller`** (a chain of `Guard`s, e.g. `IterationLimiter`) can outright deny.
A softer **`ProgressTracker`** catches "repeating the same call with the same
result" via a `cycle_signature` history — a three-valued assessment
(advancing/stalling/stalled) that **nudges once** (folding corrective guidance
into the conversation) before it stops. It is deliberately *not* a `Guard`,
because a binary go/no-go cannot express "nudge, then continue."

## Context management

`ContextManager.prepare(conversation)` is a **pure, stateless read-time
projection**: above a message threshold it keeps the leading instructions + the
original task + the most recent turns, and elides the middle behind a marker —
never orphaning a tool result (providers reject that). It is *structural*
windowing, not semantic summarization; the durable facts it would otherwise
preserve already live in the ledger. A model-based `Summarizer` is the noted next
seam. Keeping this component pure is why persistent memory is injected elsewhere
(below), not here.

## RAG

See [`rag-base.md`](rag-base.md). In short: a framework-level FastAPI corpus is
chunked, embedded (`EmbeddingModel` port → OpenAI), and stored in an in-house
numpy vector store. The Researcher's `rag_search` tool retrieves fragments
RAG-first (web fallback), emits a `DocumentsRetrieved` event, and logs each hit
as a `Source(Origin.RAG)` that drains into its report — so retrieved sources
reach the shared ledger.

## Persistent per-project memory

`ProjectMemory` is the durable counterpart to the in-run ledger: a copy-on-write
aggregate of `MemoryEntry(category, content)` that knows how to render itself as
a briefing. A `MemoryStore` port (with a `JsonMemoryStore` adapter, one file per
project) persists it. `ProjectMemoryService` is a **run-boundary seam**: it
briefs a run from memory before it starts and absorbs the run's ledger afterward.
It lives at the boundary precisely so `ContextManager` can stay pure — memory is
injected once as a briefing, not re-derived every reason turn.

## The Scribe and the Documenter

The **Scribe** is a subagent that is the *only* one with write permission,
confined to the documentation folder by a per-agent policy (below). It is **not**
a mid-run principal delegate — the coordinator tended to under-feed it. Instead
`Documenter` (an app-layer run-boundary seam, like `ProjectMemoryService`) invokes
the Scribe **after** the run with the *whole* ledger, so it reliably receives
every agent's findings and writes one file per contributing agent. The harness
stays generic: the only place that knows the name "scribe" is the app layer.

## Security / policy

The `ToolExecutor` is the single chokepoint for side effects. Before invoking any
tool it consults an **`Approver`**. `PolicyVerifier` (config-driven, `tomllib`,
no dependency) validates each call: read/write path deny-globs, workspace
confinement, command deny-lists and require-approval — all **fail-closed**. A
`CompositeApprover` chains policy + human supervision (first deny wins). The
Scribe's confinement is exactly this: a per-agent `PolicyVerifier` with
`workspace = docs_dir`, so any write outside the folder is denied before the tool
ever runs.

## Observability

Everything narrates itself on an **`EventBus`**; the core never prints. Handlers
subscribe: `ProgressView` (live CLI), `AuditLogger` (evidence). Subagents run on
their own buses; an `EventForwarder` bridges each onto the principal bus, tagging
every event with `Event.source`, so a single sink sees the whole run. The
optional `PhoenixTracer` maps that stream onto nested OpenTelemetry spans — a run
root, an `llm` span per model call, a `tool` span per tool call — with per-agent
attribution. Only the principal's stop closes the run root (a subagent's
forwarded stop must not), keeping the trace single-rooted. See
[`evidence/repo-analysis.otel.jsonl`](evidence/repo-analysis.otel.jsonl).

## Testing

196 tests, TDD throughout: pure domain tested directly; the loop and subagents
driven by a scripted `FakeChatModel` (no network); the OTel boundary smoke-tested
against a real in-memory OpenTelemetry SDK. `just validate` = ruff + pyright +
pytest.
