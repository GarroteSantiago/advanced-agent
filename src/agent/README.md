# `agent` — the application layer

Where the reusable [`harness`](../harness/) becomes *this* product: a multi-turn
conversational coordinator, a team of role-scoped subagents, plan/supervise
modes, the RAG tool, and the Scribe. This is the **only** layer that knows
application concepts — the harness never hears the words "researcher" or "scribe".

> Diagram: [`agent.puml`](agent.puml). Up one level: [`../README.md`](../README.md).
> System-wide "why": [`docs/architecture.md`](../../docs/architecture.md).

## The two nested loops

- **`Session`** ([`session.py`](session.py)) — the **outer** loop. Holds the
  running `Conversation` across user turns; each `ask(message)` runs one **inner**
  ReAct loop (built from the shared `assembly`) seeded with the accumulated
  history, then persists `result.conversation`. Owns the controller, approver,
  optional plan mode, and the subagent registry.
- The inner loop is the harness's `AgentLoop`. It ends when the model answers
  without tools; the session then waits for the next `ask`, keeping context.

## The subagent team — [`team.py`](team.py), [`subagent.py`](subagent.py)

A `Subagent` is a **constrained agent**: its own restricted tool set, role
prompt, approver, and iteration cap, running its *own* ReAct loop on its *own*
event bus. It implements the `Delegate` port, so the principal renders it into
its `ToolCatalog` and hands it a task via an ordinary tool call.

`build_subagents` wires the five delegatable roles (the spec's "different
tools/permissions per subagent"):

| Subagent | Tools | Role |
| --- | --- | --- |
| `explore` | `read_file`, `list_files` | Understand structure, architecture, deps, conventions. |
| `research` | `rag_search`* + `web_search` | Look up framework docs — **RAG-first**, web fallback. |
| `implement` | `read_file` | Propose changes as text; never applies them. |
| `test` | `read_file`, `run_command` | Run build/tests/lint to gather evidence (its `run_command` is gated by the same policy). |
| `review` | `read_file` | Check the findings answer the request. |

\* `rag_search` is added only when a `Retriever` is available.

Two behaviors worth knowing:

- **Partial findings on abort** — if a subagent's loop halts without an answer
  (iteration cap / stall), `delegate` does not hand back the bare stop reason.
  A `PartialSynthesizer` ([`synthesis.py`](synthesis.py)) runs one forced,
  tool-less recap turn, so the report is `[partial -- <reason>] <what it found>`.
- **Event forwarding** — each subagent runs on a private bus; `forward_events_to`
  bridges it onto the principal's bus (tagged with the subagent's name), so audit
  and observability see the whole run.

## The Scribe and the Documenter — [`team.py`](team.py), [`documenter.py`](documenter.py)

The **Scribe** is a subagent with the *only* write permission, **confined to the
docs folder** by a per-agent `PolicyVerifier(workspace=docs_dir)` (fail-closed;
first deny wins). It is deliberately **not** a mid-run delegate — the coordinator
tended to under-feed it. Instead `Documenter` invokes it at the **run boundary**
with the *whole* ledger, so it reliably gets every agent's findings and writes
one file per contributing agent. (A run with no findings writes nothing.)

## Other collaborators

| Type | File | Role |
| --- | --- | --- |
| `RagSearchTool` / `RetrievalLog` | [`rag_tool.py`](rag_tool.py) | The Researcher's RAG tool; bridges [`rag`](../rag/) ↔ harness. Records each hit as a `Source(Origin.RAG)` into the log the subagent drains into its report, and emits `DocumentsRetrieved`. |
| `PlanMode` / `PlanReview` | [`planning.py`](planning.py) | `/plan`: produce a numbered plan (no tools), get approve / reject / revise before acting. Sealed `PlanReview` sum type. |
| `PartialSynthesizer` | [`synthesis.py`](synthesis.py) | The forced recap turn (emits the same model events so its cost is traced). |
| `ProgressView` | [`progress.py`](progress.py) | `EventHandler` that renders live activity through the `Renderer` port; `verbose` adds phase/cycle detail. |
| `Renderer` / `Inputer` | [`interaction.py`](interaction.py) | I/O **ports** — the only place `print`/`input` are called is the console adapters, which keeps the REPL testable. |
| `build_session` / `run_chat` | [`cli.py`](cli.py) | Wire the coordinator + team + modes + progress view; drive the REPL (`/plan`, `/supervise`, `/verbose`, `/help`, `/exit`). `on_result` is the hook `main.py` uses to absorb a run into project memory. |

## Collaborators

Outward of the harness; depends on [`harness`](../harness/), [`llm`](../llm/),
[`rag`](../rag/), and [`prompts`](../prompts/). The composition root
[`main.py`](../../main.py) wires the concrete model, retriever, memory, and
observability around this layer.
