# The composition root — `main.py`

`main.py` is where the onion is assembled: the **only** place that picks concrete
adapters and injects them inward. Every port defined in the source
([`ChatModel`](../src/llm/), [`EmbeddingModel`](../src/llm/),
[`Approver`](../src/harness/tools/), [`MemoryStore`](../src/memory/),
`Renderer`/`Inputer`) gets bound to a real implementation here, so the rest of the
codebase depends on interfaces, never on OpenAI/the filesystem/the console.

> The interactive-chat entry point. The repo-analysis use case has its own root,
> [`scripts/analyze_repo.py`](../scripts/README.md), which reuses these same
> builders. Structure diagram: [`diagrams/ownership.puml`](diagrams/ownership.puml).

## What it wires (in order)

| Step | Function | What it decides |
| --- | --- | --- |
| 1. Env | `_load_dotenv()` | Loads `.env` into the environment (never overrides an already-set var). |
| 2. I/O adapters | `ConsoleRenderer` / `ConsoleInputer` | The concrete `Renderer`/`Inputer` — the only place `print`/`input` happen. |
| 3. Guardrails | `_load_policy()` | `PolicyConfig.from_toml("agent.config.toml")` if the file exists, else `None`. See [`agent.config.toml.example`](../agent.config.toml.example). |
| 4. Model | `_build_model()` | `OpenAIChatModel` when `OPENAI_API_KEY` is set, else `PlaceholderChatModel` (so the app runs keyless). |
| 5. RAG | `_build_retriever()` | Loads the persisted index into a `Retriever` **only** if a key is set and `data/rag_index/chunks.json` exists — else `None` (Researcher falls back to web). |
| 6. Memory | `_build_memory()` | A `ProjectMemoryService` over a `JsonMemoryStore`; the project id is the launch directory (`cwd`), so knowledge accrues per working tree. |
| 7. Brief | `memory.briefing(project_id)` | Renders prior-session memory to seed into the principal's prompt. |
| 8. Assemble | `build_session(...)` | Hands model + adapters + policy + retriever + briefing to [`agent/cli.py`](../src/agent/), which builds the coordinator `Session`, the subagent team, plan/supervise modes, and the live `ProgressView`. |
| 9. Observability | `_enable_observability()` | Opt-in: subscribes the Phoenix tracer when `OBSERVABILITY=phoenix`; best-effort (warns, doesn't crash, if the extra is missing). |
| 10. Run | `run_chat(..., on_result=_remember)` | Drives the REPL. `on_result` is the seam that calls `memory.absorb(project_id, result)` after each turn — the write half of persistent memory. |

## The shape to notice

```
main.py  ──picks adapters──▶  ports  ◀──depend on──  harness / agent / rag / memory
   │                                                         ▲
   └── injects: model, retriever, memory, policy, I/O, tracer ┘
```

Ports point inward; adapters are constructed here and passed down. To swap the
provider (a different model, a non-OpenAI embedder, a non-JSON memory store, a GUI
instead of the console), you change **only this file** — nothing inward moves.
That is the payoff of the dependency rule the whole [`src/`](../src/README.md) tree
is organized around.

## Related roots

- **Single-shot** — [`Harness`](../src/harness/harness.py): one task, one loop.
- **Multi-turn (this file)** — [`Session`](../src/agent/session.py) via
  `build_session`, persisting history across turns.
- **Batch/evidence** — [`scripts/analyze_repo.py`](../scripts/README.md): reuses
  `main`'s builders headlessly and prints an evidence report.
