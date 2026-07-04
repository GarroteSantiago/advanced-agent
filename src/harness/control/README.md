# `harness.control` — hard limits and soft stalls

What keeps a run *trustworthy, auditable, and contained*. Two collaborators, at
two levels of severity: a `Controller` (a chain of `Guard`s) that can **hard-deny**,
and a `ProgressTracker` that grades repetition and can **nudge before it stops**.

> Diagram: [`control.puml`](control.puml). Up one level: [`../README.md`](../README.md).

## The key design tension

A `Guard` returns a binary `Decision` (allow / deny). But a no-progress loop
deserves a *graded* response: the first repeated cycle should earn a nudge (a
chance to change strategy), and only a further repeat should stop the run. That
third state cannot fit in a boolean — so the `ProgressTracker` is deliberately
**not** a `Guard`. The controller stays purely about hard limits; the tracker
owns the three-valued "advancing / stalling / stalled" judgment. The
[`ObservationPhase`](../loop/phases/) consults them in that order.

## Key objects

| Type | File | Role |
| --- | --- | --- |
| `Guard` | [`guard.py`](guard.py) | Port: `name` + `evaluate(context) -> Decision`. Limits, policy checks, loop detection all fit this one interface. |
| `Decision` | [`decision.py`](decision.py) | Verdict: `allow()` / `deny(reason)`; `denied()`. |
| `Controller` | [`controller.py`](controller.py) | Composes guards; `permit(context)` returns the **first denial (fail-closed)**, evaluated in registration order. The typed replacement for the old untyped `running_strategy`. |
| `IterationLimiter` | [`iteration_limiter.py`](iteration_limiter.py) | A `Guard` that denies once `metadata().iterations >= max`. The hard backstop against runaway loops. |
| `ProgressTracker` | [`progress_tracker.py`](progress_tracker.py) | Grades repetition of the latest **cycle signature** over the context's signature history. `stall_at=2` → nudge, `stop_at=3` → halt (the defaults give exactly one corrective turn). |
| `Progress` / `ProgressAssessment` | [`progress_tracker.py`](progress_tracker.py) | The three-valued verdict (`ADVANCING/STALLING/STALLED`) + `advancing()/stalling()/stalled()`. |

## An important property

The tracker is a **pure function of the context**: all state (the signature
history) lives on the immutable `AgentExecutionContext`, so a single tracker
instance is safe to reuse across delegations without one run's history leaking
into the next.

## Collaborators

Depends inward only on [`runtime`](../runtime/) (reads `metadata`, iteration
count, `recorded_signatures`). Consumed by the [`ObservationPhase`](../loop/).
Deferred guard seams (`BudgetLimiter`, `ApprovalPolicy`) will implement `Guard`
and need no loop change.
