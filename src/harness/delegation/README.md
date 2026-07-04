# `harness.delegation` — the multi-agent seam

The harness-side primitives that let a principal agent hand work to subagents and
fold their contributions into the shared task state. The *concrete* subagents (the
team) live outward in [`agent/`](../../agent/); this package is just the port and
the roster.

> Diagram: [`delegation.puml`](delegation.puml). Up one level: [`../README.md`](../README.md).

## The central trick

A `Delegate` is `Describable` (`name`/`description`/`parameters`) — exactly the
shape the principal's `ToolCatalog` renders to the model. So a subagent appears
to the model as **just another tool**, and the model *chooses* delegation by
emitting an ordinary tool call. The [`DelegatingActionPhase`](../loop/phases/)
then routes calls whose name the registry `knows()` to the subagent instead of
the executor.

## Key objects

| Type | File | Role |
| --- | --- | --- |
| `Delegate` | [`delegate.py`](delegate.py) | Port: `Describable` + `async delegate(task) -> SubagentReport`. |
| `SubagentRegistry` | [`delegate.py`](delegate.py) | The principal's roster: `knows(name)`, `resolve(name)` (raises `UnknownSubagentError`), `all()`. |
| `SubagentReport` | [`report.py`](report.py) | Immutable summary of one subagent's contribution: `agent`, `output`, `succeeded`, and the `sources` / `modified_files` / `observations` to merge. `completed`/`failed` factories. |

## How a report reaches the shared ledger

`SubagentReport` is the bridge between a subagent's *private* run and the shared
[`TaskLedger`](../runtime/). The delegating action phase folds each report in:
`crediting` a `SubagentResult`, then merging every `source`, `modified_file`, and
`observation`. Because the ledger is copy-on-write, this merge never mutates a
ledger the principal is still reading. That is how the spec's *estado compartido*
comes to record subagent work.

**Delegation cannot recurse:** subagents run the plain `ActionPhase`, so they are
never handed a delegating phase.

## Collaborators

Depends inward on [`runtime`](../runtime/) (`Source` on the report). Consumed by
the [`DelegatingActionPhase`](../loop/) and populated at the app layer by
[`agent/team.py`](../../agent/).
