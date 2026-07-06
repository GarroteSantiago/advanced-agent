# `observability` — event stream → external traces

Turns the harness [`EventBus`](../harness/events/) stream into nested
OpenTelemetry spans for a Phoenix UI. Split into a **pure mapping** (no
dependency) and a **thin SDK boundary** — the same split
[`OpenAIChatModel`](../llm/) uses — so the interesting logic is unit-testable
without installing Phoenix.

> Diagram: [`observability.puml`](observability.puml). Up one level: [`../README.md`](../README.md).
> Live trace evidence: [`docs/evidence/repo-analysis.otel.jsonl`](../../docs/evidence/repo-analysis.otel.jsonl).

## Two layers

| Layer | File | Depends on OTel? |
| --- | --- | --- |
| Pure span mapping | [`spans.py`](spans.py) | **No** — exported from the package `__init__`. |
| Phoenix/OTel boundary | [`phoenix.py`](phoenix.py) | Yes — imported directly by [`main.py`](../../main.py) only when observability is enabled. |

## Key objects

| Type | File | Role |
| --- | --- | --- |
| `SpanData` | [`spans.py`](spans.py) | Provider-neutral span: `name` + OpenInference-style `attributes`. |
| `llm_span` / `tool_span` | [`spans.py`](spans.py) | Pure functions pairing a start+end event into one `SpanData` (tokens, latency, cost, per-agent `agent.name`). |
| `PhoenixTracer` | [`phoenix.py`](phoenix.py) | `EventHandler` that builds the span tree: pairs `ModelCalled`+`ModelCompleted` and `ToolInvoked`+`ToolObserved` (by `call_id`) so spans carry real durations. |
| `launch_phoenix_tracer` | [`phoenix.py`](phoenix.py) | Lazily imports Phoenix, launches the local UI, returns a wired tracer. |

## The single-root invariant

Every event first ensures a run root (`agent.run`, kind `CHAIN`). Under it hang an
`llm` span per model call and a `tool` span per tool call. Crucially, **only the
principal's `LoopStopped` closes the root** — a subagent's stop is forwarded with
`source != ""` and must *not* close it, or the subagent's own activity would fall
outside the run tree. That plus the `source` tag on every event (set by the
[`EventForwarder`](../harness/events/)) is what makes the trace single-rooted with
per-agent attribution.

## Collaborators

Depends inward on [`harness.events`](../harness/events/) (the event types).
Subscribed to the session bus in [`main.py`](../../main.py) when
`OBSERVABILITY=phoenix`. Enable the extra with `uv sync --extra observability`.
