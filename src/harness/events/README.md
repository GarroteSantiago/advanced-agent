# `harness.events` — the narration substrate

Everything narrates itself on an **`EventBus`**; the core never prints. Handlers
subscribe. This is the substrate for *all* observability — the live CLI view, the
audit trail, and the optional OpenTelemetry tracer are all just handlers.

> Diagram: [`events.puml`](events.puml). Up one level: [`../README.md`](../README.md).

## Key objects

| Type | File | Role |
| --- | --- | --- |
| `Event` | [`event.py`](event.py) | Frozen base: `occurred_at` (timestamped at creation) + `source` (the emitting agent — empty for the principal, the subagent's name once forwarded). |
| Event subtypes | [`event.py`](event.py) | `PhaseStarted/Completed`, `ModelCalled`, `ModelCompleted` (tokens, latency, `cost_usd`), `ToolInvoked`, `ToolObserved`, `DocumentsRetrieved`, `CycleCompleted`, `LoopStopped`, `GuardTripped`, `StrategyNudged`. |
| `EventHandler` | [`handler.py`](handler.py) | Port: `handle(event) -> None`. |
| `EventBus` | [`bus.py`](bus.py) | Synchronous in-process fan-out. `subscribe` returns a `Subscription`; `publish` iterates a **snapshot** so a handler may unsubscribe mid-dispatch. |
| `Subscription` | [`bus.py`](bus.py) | A cancel-once link — callers never reach into the bus's handler list. |
| `AuditLogger` | [`audit.py`](audit.py) | The minimal sink: records every event in order as an immutable trail (`records()`). |
| `EventForwarder` | [`forwarder.py`](forwarder.py) | Bridges one bus onto another, stamping each event with `source`. |

## The dual-bus pattern (why forwarding exists)

A subagent runs its inner loop on its **own** bus, so its activity never reaches
the principal's bus directly. An `EventForwarder` subscribes to the subagent's
bus and republishes each event onto the principal's, stamped with the subagent's
name. Keeping the buses separate preserves each subagent's isolation *and* lets
the forwarded copy carry `source` — the provenance a nested trace and per-agent
accounting both need. The forwarder is never subscribed to its own target, so
there is no republish loop.

```
subagent bus  --(EventForwarder: replace(event, source="researcher"))-->  principal bus
                                                                            |
                                       ProgressView · AuditLogger · PhoenixTracer  (handlers)
```

## Collaborators

Depends inward on nothing but stdlib. Published to by nearly every harness
component; subscribed to by the app layer's [`ProgressView`](../../agent/) and
[`observability`](../../observability/) tracer.
