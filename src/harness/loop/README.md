# `harness.loop` — the ReAct cycle as a dumb driver + an explicit graph

The loop is deliberately stupid: it runs a **phase**, then asks a **`Navigator`**
what to do next. All routing lives in the navigator's transition table; all
mutable state lives in the immutable [`AgentExecutionContext`](../runtime/). The
loop knows neither the graph nor the run state.

> Diagrams: [`loop.puml`](loop.puml) (the transition table as a state machine) —
> and the top-level [`docs/diagrams/sequence.puml`](../../../docs/diagrams/sequence.puml)
> for one turn step-by-step. Up one level: [`../README.md`](../README.md).

## Why a navigator instead of `if/else` in the loop

A phase reports an `Outcome`; it does **not** decide what runs next. That keeps
phases decoupled from each other and makes the whole graph — continuing edges
*and* exits — visible in one table built at the composition root
([`assembly.py`](../assembly.py)). Two design choices fall out:

- **`Transition` is a sealed sum type** — `Continue(next_phase) | Halt`, never a
  `None` sentinel. It extends cleanly to a third case (`AwaitInput`, "ask for
  help") that a boolean could not express.
- **An unmapped `(phase, outcome)` raises `UnknownTransitionError`** — a wiring
  bug fails loudly instead of silently halting.

## Key objects

| Type | File | Role |
| --- | --- | --- |
| `AgentLoop` | [`agent_loop.py`](agent_loop.py) | The driver. `run(context)`: start at `navigator.start()`, and while the transition is `Continue`, `step` the phase and ask `navigator.next(phase, outcome)`. Publishes `PhaseStarted/PhaseCompleted/LoopStopped`, returns `ExecutionResult`. |
| `Navigator` | [`navigator.py`](navigator.py) | Maps `(current phase, outcome) → Transition` from an explicit table. `start()` + `next()`. |
| `Transition` / `Continue` / `Halt` | [`navigator.py`](navigator.py) | The sealed answer type. `Halt` is a pure control marker — the terminal *reason* lives on the context. |
| `Phase` | [`phase.py`](phase.py) | `Protocol`: a `name` and `async run(context) -> PhaseResult`. |
| `Outcome` | [`phase.py`](phase.py) | The phase-report vocabulary: `TOOLS_REQUESTED`, `ANSWERED`, `ACTED`, `CONTINUE`, `DENIED`. |
| `PhaseResult` | [`phase.py`](phase.py) | `(advanced context, outcome)`. |

### The three phases — [`phases/`](phases/)

| Phase | Collaborator | Behavior | Outcome(s) |
| --- | --- | --- | --- |
| `ReasonPhase` | `ChatModel`, `ToolCatalog`, `ContextManager` | Projects history through the context manager (windowing), calls the model, folds the turn into the **full** context. Emits `ModelCalled`/`ModelCompleted` (with cost). | `TOOLS_REQUESTED` or `ANSWERED` (→ `stopped`) |
| `ActionPhase` | `ToolExecutor` | Runs each pending tool call, records touched files (`touching_all`), stashes results. | `ACTED` |
| `ObservationPhase` | `Controller`, `ProgressTracker` | `observed()` closes the cycle; the controller can hard-`DENY`; the tracker can nudge-once (folding advice via `advised`) or stall-stop. | `CONTINUE` or `DENIED` (→ `aborted`) |
| `DelegatingActionPhase` | `ToolExecutor`, `SubagentRegistry` | Principal-only variant of `ActionPhase`: routes subagent calls to the team and **merges** each `SubagentReport` into the shared ledger. See below. | `ACTED` |

## The transition table (wired in [`assembly.py`](../assembly.py))

```
start: reason
  (reason,      TOOLS_REQUESTED) -> Continue(action)
  (reason,      ANSWERED)        -> Halt
  (action,      ACTED)           -> Continue(observation)
  (observation, CONTINUE)        -> Continue(reason)
  (observation, DENIED)          -> Halt
```

That is the ReAct cycle: **reason → act → observe → reason …** until the model
answers (`Halt` from reason) or a limit/stall denies (`Halt` from observation).

## Delegation seam

`build_agent_loop` picks the action phase by whether `subagents` was supplied:
the **principal** loop gets `DelegatingActionPhase` and a `ToolCatalog` that
renders both tools *and* subagents; a **subagent** loop gets the plain
`ActionPhase`. Because subagents never get the delegating phase, **delegation
cannot recurse.** See [`../delegation/`](../delegation/).

## Collaborators

Inward: [`runtime`](../runtime/) (context/result), [`llm`](../../llm/) (`ChatModel`).
Sideways within the harness: [`tools`](../tools/), [`control`](../control/),
[`context`](../context/), [`events`](../events/), [`delegation`](../delegation/).
Wired by [`assembly.py`](../assembly.py), driven by [`agent`](../../agent/)'s
`Session`/`Harness`.
