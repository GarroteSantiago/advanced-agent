# `harness.context` — what enters the model's window

One class, `ContextManager`. A **pure, stateless read-time projection**: given
the full immutable conversation it returns the (possibly smaller) view to send
to the model *this turn*. It never mutates or truncates the persisted history —
the [`AgentExecutionContext`](../runtime/) keeps the whole record and each reason
turn re-projects it.

> Up one level: [`../README.md`](../README.md).

## What it does (and deliberately does not)

The policy is **structural windowing**, not semantic summarization. Above
`max_messages` it keeps:

```
[ leading system instructions ] + [ the original user task ]      <- head, always kept
[ "N earlier messages elided …" marker ]                          <- the elided middle
[ the most recent keep_recent turns, verbatim ]                   <- safe tail
```

Two correctness invariants:

- **Never orphan a tool result.** A `tool` message whose assistant `tool_calls`
  was elided is rejected by providers, so `_safe_tail_start` steps the tail
  forward past any leading `tool` message to the next self-contained turn.
- **Non-destructive.** If nothing can be safely elided, it returns the
  conversation unchanged. Durable facts it would otherwise preserve already live
  in the `TaskLedger`.

Defaults: `max_messages=40`, `keep_recent=12`.

## Why it stays pure

Keeping this component a pure function is *why* persistent memory is injected
elsewhere (the app-layer `ProjectMemoryService` briefs a run once at its
boundary) rather than re-derived here every reason turn. A model-based
`Summarizer` that turns the elided span into prose instead of a marker is the
noted next seam.

Depends inward only on [`llm`](../../llm/) (`Conversation`, `Message`, `Role`).
Consumed by the [`ReasonPhase`](../loop/phases/).
