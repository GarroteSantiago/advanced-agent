# `llm` — conversation value objects + the model ports

The innermost ring. Pure domain data for talking to a language model, plus the
two **ports** the rest of the harness depends on (`ChatModel`, `EmbeddingModel`).
Concrete providers live outward in [`providers/`](providers/) and are wired in at
the composition root ([`main.py`](../../main.py)); nothing here imports them.

> Diagram: [`llm.puml`](llm.puml) — value objects, ports, and the adapters that
> implement them. Up one level: [`../README.md`](../README.md).

## Why this shape

The port is **message-oriented** — it speaks `Conversation` in and `Completion`
out — not an anemic `send(str) -> str`. That is what lets it express tool use at
all: a completion can carry `tool_calls`, and a conversation can carry tool
results. Behavior that belongs to the data lives *on* the data, so collaborators
never reach into raw lists (`Conversation` owns how messages accumulate,
`Completion` knows whether it is asking for tools, `TokenUsage` knows how to sum).

## Key objects

### Value objects — [`messages.py`](messages.py)

| Type | Role | Invariants / key messages |
| --- | --- | --- |
| `Role` | `StrEnum` of `system/user/assistant/tool`. | Authorship as chat models understand it. |
| `Message` | One turn. | Frozen, `slots`. Built through role factories (`Message.system/user/assistant/tool`) so callers state intent instead of juggling optional fields (`tool_calls`, `tool_call_id`, `name`). |
| `ToolCall` | A model's request to invoke a named tool. | Frozen; `id`, `name`, `arguments`. |
| `TokenUsage` | Token accounting for one call. | Frozen; `total()` and `__add__` make usage summable across calls. |
| `Completion` | What a model produced for one call. | `requests_tools()` is the question the loop asks — it keeps the `len(tool_calls)` check off the phases. Carries `content`, `tool_calls`, `stop_reason`, `usage`. |
| `Conversation` | Immutable, append-only message sequence. | Backing tuple never exposed mutably: `with_message`/`with_messages` return a **new** conversation; `messages()` hands back an immutable view. Build with `empty()`/`of()`. |
| `ToolSchema` | `Mapping[str, object]` type alias — one provider-neutral tool schema. | The *only* thing a `ChatModel` needs to know about tools, so the model port never depends on the tool subsystem. |

### Ports — [`ports/`](ports/)

| Port | Contract | Notes |
| --- | --- | --- |
| `ChatModel` | `identifier() -> str`, `async complete(conversation, *, tools=None) -> Completion`. | `runtime_checkable` `Protocol`. `tools` are already-rendered `ToolSchema`s (see `ToolCatalog.for_model`); the model decides answer-vs-tools. |
| `EmbeddingModel` | `identifier() -> str`, `async embed(texts) -> list[list[float]]`. | Batch-oriented so ingestion embeds a whole chunk set in as few provider calls as possible. Depended on by [`rag/`](../rag/). |

### Adapters (outer ring) — [`providers/`](providers/)

| Adapter | Implements | Notes |
| --- | --- | --- |
| `OpenAIChatModel` | `ChatModel` | Wraps `AsyncOpenAI`. The Conversation↔OpenAI translation is done by the **pure module functions** `encode_messages` / `encode_tools` / `decode_completion`, unit-tested without the network; `Any` appears only at the untyped SDK boundary. |
| `OpenAIEmbeddingModel` | `EmbeddingModel` | Thin wrapper over the OpenAI embeddings endpoint; batch in, vectors out. |
| `PlaceholderChatModel` | `ChatModel` | Never calls tools, returns a fixed notice — lets the CLI and full loop run end-to-end with no API key. |

### Cost — [`pricing.py`](pricing.py)

`estimate_cost(model, usage) -> float` — a small, updatable `_RATES` lookup (USD
per 1M tokens, prompt/completion split). The spec asks for an *estimate*, not
billing accuracy; unknown models cost `0.0` (an honest zero over a wrong number).

## Collaborators

Depended on by nearly every outer ring — the loop's `ReasonPhase` calls
`ChatModel.complete`, `rag` calls `EmbeddingModel.embed`, the runtime `TaskLedger`
accumulates `TokenUsage`, and `agent/cli.py` reports `estimate_cost`. This package
imports **nothing** from the harness — the dependency rule points inward, here.
