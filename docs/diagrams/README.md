# Architecture diagrams

PlantUML diagrams to onboard someone to the agent. Start with the overview for
the whole picture, then read the rest in order for detail.

| File | View | Question it answers |
| --- | --- | --- |
| [`overview.puml`](overview.puml) | **System overview (start here)** | Everything on one canvas: the layers, the loop, the subagent team, RAG/memory/observability, and the main flows between them. |
| [`ownership.puml`](ownership.puml) | **Ownership / structure** | Who constructs and owns what? Where do dependencies come from? |
| [`runtime-collaboration.puml`](runtime-collaboration.puml) | **Runtime collaboration** | Which objects send which messages during a turn? |
| [`sequence.puml`](sequence.puml) | **Sequence** | Step by step, what happens in one ReAct turn that uses a tool? |

For the per-package drill-down (each `src/` package's own README + a diagram at
its abstraction level), start at [`../../src/README.md`](../../src/README.md).

## The 60-second mental model

- A **`Session`** (agent layer) holds the conversation across turns. Each `ask()` builds a
  fresh **`AgentLoop`** over an immutable **`AgentExecutionContext`**.
- The loop is a dumb driver: it runs a **phase**, then asks the **`Navigator`** what's next.
  The navigator returns `Continue(nextPhase)` or `Halt`. The graph is one table.
- The three phases are the ReAct cycle:
  - **`ReasonPhase`** asks the **`ChatModel`** what to do (answer, or call tools).
  - **`ActionPhase`** runs the tool calls through the **`ToolExecutor`**.
  - **`ObservationPhase`** folds the results back in and asks the **`Controller`** whether to continue.
- The **`ToolExecutor`** is the single chokepoint for side effects: it consults an **`Approver`**
  (supervision + policy guardrails) before invoking any **`ToolInterface`**.
- Everything narrates itself on the **`EventBus`**; handlers like **`ProgressView`** (live CLI
  output) and **`AuditLogger`** (trace) subscribe. The core never prints.
- Ports (interfaces) point inward: `ChatModel`, `ToolInterface`, `Approver`, `Renderer`/`Inputer`.
  Adapters (OpenAI, the five tools, console I/O) live on the outside and are wired in `main.py`.

## Rendering

These are plain PlantUML. To produce images:

```sh
# with the PlantUML CLI (needs Java + Graphviz)
plantuml docs/diagrams/*.puml          # -> PNG next to each .puml
plantuml -tsvg docs/diagrams/*.puml    # -> SVG
```

Or paste a file into the [PlantUML web server](https://www.plantuml.com/plantuml),
or use the PlantUML extension in VS Code / JetBrains for live preview.
