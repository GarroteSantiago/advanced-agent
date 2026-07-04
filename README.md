# advanced-agent

A coding-agent **harness** evolved into a fuller system — multi-agent delegation,
RAG, persistent per-project memory, context/loop management, config-driven
security policies, and observability — built **without any orchestration
framework** (no LangChain/LangGraph). Core dependencies are just `openai` and
`tavily-python`, plus an optional observability extra.

The delivered use case: **analyze an unknown FastAPI repository** and produce a
verifiable report (architecture, dependencies, risks, commands), writing the
findings to a documentation folder. See [`docs/use-case.md`](docs/use-case.md).

- **Python:** 3.11.9 (pinned via `.python-version`) · **Package manager:** `uv` · **Task runner:** `just`

## Documentation

| Doc | What it covers |
| --- | --- |
| [`docs/architecture.md`](docs/architecture.md) | Onion layers, the loop/navigator/phases, delegation, control, RAG, memory, observability, the Scribe. |
| [`docs/diagrams/`](docs/diagrams/) | PlantUML: ownership, runtime collaboration, one ReAct turn. |
| [`src/README.md`](src/README.md) | **Per-package drill-down**: every `src/` package has its own README (down to key classes) + a PlantUML diagram at its abstraction level. Start here to read the tree. |
| [`docs/composition-root.md`](docs/composition-root.md) | How `main.py` wires the onion — which concrete adapters get injected inward, step by step. |
| [`docs/use-case.md`](docs/use-case.md) | The concrete objective, the team, success criteria. |
| [`docs/rag-base.md`](docs/rag-base.md) | The RAG corpus, pipeline, and how to build the index. |
| [`docs/evidence/`](docs/evidence/) | Live-run evidence: executed-task demos + an OpenTelemetry trace. |
| [`docs/reproduce.md`](docs/reproduce.md) | Step-by-step: regenerate every generated deliverable (index, evidence, trace). |
| [`docs/reflection.md`](docs/reflection.md) | What worked, what was hard, honest limitations. |

## Install

Requires [`uv`](https://docs.astral.sh/uv/getting-started/installation/) and
[`just`](https://github.com/casey/just#installation).

```sh
git clone <repository-url>
cd advanced-agent
uv sync                          # core install (provisions Python 3.11.9)
uv sync --extra observability    # optional: adds Phoenix/OpenTelemetry
```

## Configure

Copy `.env.sample` to `.env` and fill in what you need (`.env` is gitignored):

| Variable | Purpose | Default |
| --- | --- | --- |
| `OPENAI_API_KEY` | Enables the OpenAI provider (else a placeholder model). | — |
| `MODEL` | Chat model. | `gpt-5-nano` |
| `TAVILY_API_KEY` | Enables the `web_search` tool. | — |
| `EMBED_MODEL` | Embedding model for RAG. | `text-embedding-3-small` |
| `RAG_INDEX_DIR` | Persisted vector index location. | `data/rag_index` |
| `MEMORY_DIR` | Per-project memory store. | `data/memory` |
| `DOCS_DIR` | Folder the Scribe writes results into (it is confined here). | `docs/analysis` |
| `OBSERVABILITY` | `phoenix` (UI) or `otel-file` (JSONL) — else off. | off |
| `OTEL_TRACE_FILE` | Trace output for `otel-file` mode. | `otel-trace.jsonl` |

Optional **security guardrails** live in `agent.config.toml` (loaded if present):
copy [`agent.config.toml.example`](agent.config.toml.example) and edit it. See the
schema and fail-closed semantics in [`src/harness/tools/README.md`](src/harness/tools/README.md).

## Run

### Interactive chat

```sh
just run          # or: uv run python main.py
```

A REPL with `/plan`, `/supervise`, `/verbose`, `/help`, `/exit`. It briefs from
this working directory's project memory and delegates to the subagent team.

### Analyze a repository (the use case)

```sh
# build the RAG index once (needs OPENAI_API_KEY):
python scripts/ingest_rag.py

# analyze a target repo (defaults to the committed scripts/sample_app fixture):
python scripts/analyze_repo.py [TARGET_DIR]
```

This runs one analysis through the principal coordinator and prints an **evidence
report** (subagent results, sources by origin, loop behaviour, tokens/latency/cost),
then the Scribe writes one file per agent into `DOCS_DIR`. To capture a trace:

```sh
OBSERVABILITY=otel-file OTEL_TRACE_FILE=trace.jsonl python scripts/analyze_repo.py
```

## Project layout

```
main.py                     # CLI entry point (composition root)
scripts/
  analyze_repo.py           # the repo-analysis driver (evidence report)
  ingest_rag.py             # build the RAG index from the corpus
  sample_app/               # a small FastAPI fixture to analyze
src/
  llm/         # message value objects, ChatModel/EmbeddingModel ports, OpenAI adapter
  harness/     # runtime (context+ledger), loop, tools, control, context, events, delegation
  agent/       # Session, Subagent, team, Documenter, RAG tool, planning, progress, CLI
  rag/         # chunk, embed, vector store, retrieve, ingest
  memory/      # ProjectMemory, JsonMemoryStore, ProjectMemoryService
  observability/  # pure span mapping + Phoenix/OTel boundary
  prompts/     # role prompts
  tests/       # 196 tests
```

## Developer tasks

| Recipe | Command | Purpose |
| --- | --- | --- |
| `just run` | `uv run python main.py` | Run the interactive chat. |
| `just test` | `uv run pytest` | Run the test suite. |
| `just lint` | `uv run ruff check --fix .` | Lint + auto-fix (Ruff; 8-space indent, line 110). |
| `just format` | `uv run ruff format .` | Format. |
| `just type` | `uv run pyright` | Type-check. |
| `just validate` | lint + type + test | Full gate before committing. |
