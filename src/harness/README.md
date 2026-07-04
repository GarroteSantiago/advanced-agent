# `harness` — everything that acts during a task

The reusable coding-agent core. It interleaves reasoning, action, and observation
([`loop`](loop/)); lets the agent perceive and alter its environment
([`tools`](tools/)); holds the shared, immutable run state ([`runtime`](runtime/));
decides what enters the model's window ([`context`](context/)); keeps the run
contained and auditable ([`control`](control/), [`events`](events/)); and exposes
the multi-agent seam ([`delegation`](delegation/)). It depends on nothing but
[`llm`](../llm/) — no application concepts (no "researcher", no "scribe") leak in.

> Diagram: [`harness.puml`](harness.puml). Up one level: [`../README.md`](../README.md).
> System-wide "why": [`docs/architecture.md`](../../docs/architecture.md).

## Subpackages (each has its own README)

| Package | Responsibility | Drill-down |
| --- | --- | --- |
| [`runtime/`](runtime/) | The immutable `AgentExecutionContext` spine + the shared `TaskLedger`. | [README](runtime/README.md) |
| [`loop/`](loop/) | The ReAct cycle: `AgentLoop` + `Navigator` + the three phases. | [README](loop/README.md) |
| [`tools/`](tools/) | The side-effect chokepoint: `ToolExecutor`, registry/catalog, approval + policy, adapters. | [README](tools/README.md) |
| [`control/`](control/) | Hard limits (`Guard`/`Controller`) and graded stalls (`ProgressTracker`). | [README](control/README.md) |
| [`context/`](context/) | `ContextManager` — pure windowing of the model's view. | [README](context/README.md) |
| [`events/`](events/) | `EventBus`, events, handlers, `EventForwarder` — the narration substrate. | [README](events/README.md) |
| [`delegation/`](delegation/) | `Delegate` port + `SubagentRegistry` + `SubagentReport` — the multi-agent seam. | [README](delegation/README.md) |

## Composition roots

Two entry points wire the same phase graph (via [`assembly.py`](assembly.py)):

- **`Harness`** ([`harness.py`](harness.py)) — a **single-shot** root: wire bus,
  registry, controller; on each `run(task)` assemble a loop around a fresh
  context. Good for one task, tests, and scripts.
- **`Session`** ([`../agent/session.py`](../agent/)) — the **multi-turn** root:
  reuses the same assembly but persists conversation/ledger across user turns and
  adds modes (`/plan`, `/supervise`) and the subagent team.

`assembly.build_agent_loop` is the **single place the phase graph is wired** —
adding a phase or rerouting the graph happens there, and it is what selects the
delegating vs plain action phase (principal vs subagent).

## The one rule

Inner rings never import outer ones. Ports (`ChatModel`, `ToolInterface`,
`Approver`, `Guard`, `EventHandler`, `Delegate`) are defined **inward**; adapters
(OpenAI, the tools, console I/O, the JSON store) live **outward** and are wired at
the composition root. That is what makes this package reusable and every collaborator swappable at one seam.
