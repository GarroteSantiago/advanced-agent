# `src` — the source tree, as an onion

This is the drill-down map of the codebase. Each package below has its **own
README** documenting its responsibility, key classes, and collaborations, plus a
PlantUML diagram at that package's abstraction level. Start here, then follow the
links down.

> Whole-system summary: [`docs/diagrams/overview.puml`](../docs/diagrams/overview.puml)
> (start here). Package-level dependency diagram: [`src.puml`](src.puml).
> System-wide "why": [`docs/architecture.md`](../docs/architecture.md).

## The rings (inner → outer)

| Ring | Package | Responsibility | README |
| --- | --- | --- | --- |
| **0 (core)** | [`llm/`](llm/) | Conversation value objects + the `ChatModel`/`EmbeddingModel` ports. Imports nothing. | [→](llm/README.md) |
| **1 (harness)** | [`harness/`](harness/) | The reusable agent core: runtime, loop, tools, control, context, events, delegation. Depends only on `llm`. | [→](harness/README.md) |
| **1 (services)** | [`rag/`](rag/) | Chunk/embed/store/retrieve over a framework corpus. | [→](rag/README.md) |
| | [`memory/`](memory/) | Persistent per-project memory (aggregate + store + run-boundary service). | [→](memory/README.md) |
| | [`observability/`](observability/) | Pure event→span mapping + the Phoenix/OTel boundary. | [→](observability/README.md) |
| **2 (app)** | [`agent/`](agent/) | *This* product: coordinator `Session`, the subagent team, Scribe, plan/supervise modes, CLI. | [→](agent/README.md) |
| **support** | [`prompts/`](prompts/) | Role prompts (wording kept out of behavior). | [→](prompts/README.md) |
| | [`common/`](common/) | Shared kernel — intentionally near-empty. | [→](common/README.md) |
| | `tests/` | 196 tests, TDD throughout (pure domain direct; loop/subagents driven by a scripted fake model; OTel boundary against a real in-memory SDK). | — |

## The one rule (dependency direction)

Inner rings never import outer ones. **Ports** (`ChatModel`, `ToolInterface`,
`Approver`, `Guard`, `EventHandler`, `Delegate`, `MemoryStore`, `VectorStore`,
`EmbeddingModel`, `Renderer`/`Inputer`) are defined **inward**; **adapters**
(OpenAI, the tools, the JSON store, the numpy store, console I/O, the Phoenix
tracer) live **outward** and are wired at the composition root
([`../main.py`](../main.py) and [`agent/cli.py`](agent/cli.py)). That is what
keeps `harness` reusable and every collaborator swappable at one seam.

## Two composition roots

- **`Harness`** ([`harness/harness.py`](harness/harness.py)) — single-shot: one
  task, one loop. Good for scripts and tests.
- **`Session`** ([`agent/session.py`](agent/session.py)) — multi-turn: persists
  history across user turns, adds modes and the subagent team.

Both wire the **same** phase graph through
[`harness/assembly.py`](harness/assembly.py) — the single place the ReAct loop is
assembled. For how the outermost adapters (model, retriever, memory, policy, I/O,
tracer) get injected, see the composition-root walkthrough:
[`docs/composition-root.md`](../docs/composition-root.md).

## Reading order for a newcomer

1. [`docs/diagrams/`](../docs/diagrams/) — the 60-second mental model.
2. [`llm/`](llm/) → [`harness/runtime/`](harness/runtime/) →
   [`harness/loop/`](harness/loop/) — the spine and the cycle.
3. [`harness/tools/`](harness/tools/), [`harness/control/`](harness/control/) —
   side effects and containment.
4. [`agent/`](agent/) — how it all becomes the repo-analysis product.
