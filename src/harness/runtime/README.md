# `harness.runtime` — the immutable execution spine + shared task state

Every phase of the loop reads from and writes to one object,
`AgentExecutionContext`, which carries a `TaskLedger` of structured task state.
Both are **immutable and copy-on-write**: a transition returns a *new* value, so
one phase can never corrupt state another is reading, and internal tuples are
never handed out mutably. This is the anti-anemic heart of the harness.

> Diagram: [`runtime.puml`](runtime.puml). Up one level: [`../README.md`](../README.md).

## Why immutable + copy-on-write

Two payoffs. (1) **Safety within a turn** — phases hand contexts forward, never
mutate shared state. (2) **Safe sharing across agents** — because recording a
fact returns a new ledger, the principal and its subagents can share one ledger:
merging a subagent's report never mutates a ledger someone else is reading (see
[`../delegation/`](../delegation/)).

One invariant to remember: **one iteration == one model call.** Only
`with_assistant` advances the iteration count (and accumulates token usage);
`observed()` deliberately does not. That is what the `IterationLimiter` caps.

## Key objects

### `AgentExecutionContext` — [`context.py`](context.py)

The frozen spine threaded through the loop. Built with
`AgentExecutionContext.for_task(task_id, conversation, request=...)`.

**Queries:** `current_conversation()`, `pending_tool_calls()`,
`has_pending_actions()`, `state()`, `metadata()`, `ledger()`, `final_output()`,
`stop_reason()`.

**Cycle fingerprinting:** `cycle_signature()` builds a stable fingerprint of the
current *calls ⇒ results*; `observed()` appends it to `recorded_signatures()`.
This history is what the [`ProgressTracker`](../control/) reads to notice "same
call, same result, no progress."

**Transitions (copy-on-write):**

| Message | Effect |
| --- | --- |
| `with_assistant(completion)` | Append the assistant turn, set pending tool calls, **increment iteration**, add token usage, state → `REASONING`. |
| `with_tool_results(results)` | Stash the cycle's `ToolResult`s, state → `ACTING`. |
| `observed()` | Fold tool results into the conversation, record the cycle signature, clear pending, state → `OBSERVING`. Does **not** increment. |
| `stopped(output)` | Set final output, state → `COMPLETED`. |
| `aborted(reason)` | State → `ABORTED` with a stop reason. |
| `advised(note)` | Fold harness steering in as a **user-role** message (user-role is the portable way to steer a chat model mid-run). |
| `noting_progress` / `crediting` / `consulting` / `touching` / `touching_all` / `observing_that` | Delegate to the ledger transitions below. |

### `TaskLedger` — [`ledger.py`](ledger.py)

The spec's *shared task state* (`estado compartido`): beyond the raw
conversation it records `original_request`, `progress`, `subagent_results`,
`sources_consulted`, `modified_files`, `observations`. Immutable; each `with_*`
returns a new ledger. `with_modified_file` **dedupes** (recording the same path
twice is a no-op).

### `Source` + `Origin` — [`ledger.py`](ledger.py)

Provenance travels *with* the fact, not in a comment. `Origin` tags a source as
`REPO / MEMORY / RAG / WEB / INFERENCE` — answering the spec's "differentiate
repo vs memory vs RAG vs web vs inference." Build via factories:
`Source.from_repo/from_memory/from_rag/from_web/inferred`.

### `SubagentResult` — [`ledger.py`](ledger.py)

What a subagent handed back: `agent`, `summary`, `succeeded`. Factories
`SubagentResult.completed(...)` / `.failed(...)`.

### `ExecutionMetadata` — [`metadata.py`](metadata.py)

Per-run bookkeeping: `task_id`, `iterations`, `usage` (`TokenUsage`),
`started_at`. Immutable; `incremented()` / `add_usage(usage)`.

### `ExecutionState` — [`state.py`](state.py)

A plain enum (`IDLE / REASONING / ACTING / OBSERVING / COMPLETED / ABORTED`),
not a State-pattern object — transitions are owned by the context, so there is no
per-state behavior to model. `is_terminal()` covers `COMPLETED`/`ABORTED`.

### `ExecutionResult` — [`result.py`](result.py)

The terminal outcome of `AgentLoop.run`: `final_output`, `state`, `metadata`,
`conversation` (so a multi-turn session can persist history), `ledger` (so
callers can read the shared task state), `stop_reason`. `from_context(...)`
projects it out of a context; `succeeded()` is `state is COMPLETED`.

## Collaborators

Depends inward on [`llm`](../../llm/) (`Conversation`, `Completion`,
`TokenUsage`, `Message`, `ToolCall`) and on [`tools`](../tools/) for `ToolResult`.
Consumed by [`loop`](../loop/) (phases drive the transitions), [`control`](../control/)
(reads signatures/metadata), [`delegation`](../delegation/) (merges reports into
the ledger), and the app layer's memory/observability seams.
