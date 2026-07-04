# `tests` — how the system is verified

196 tests, **TDD throughout**. The strategy follows the onion: pure domain is
tested directly; the loop and subagents are driven by a scripted fake model (no
network); the outer SDK boundaries are either smoke-tested against a real
in-memory SDK or left to the adapter's own translation functions.

> Up one level: [`../README.md`](../README.md). The system-wide "Testing" note:
> [`docs/architecture.md`](../../docs/architecture.md#testing).

## Layout & config

- One `test_<module>.py` per source module (e.g. `test_loop.py`, `test_policy.py`,
  `test_memory_service.py`) — the file map mirrors the package tree, so the test
  for any unit is where you'd expect.
- Configured in [`pyproject.toml`](../../pyproject.toml): `testpaths = ["src/tests"]`,
  `pythonpath = ["src"]`, `asyncio_mode = "auto"` (so `async def test_…` needs no
  `@pytest.mark.asyncio`). No `conftest.py` — fixtures are local or built inline.
- Ruff lints the tests too, with `PT` (pytest style), `TID` (import-boundary
  guardrails), and `ANN` (require annotations) enabled — the type annotations in
  tests are load-bearing (see doubles below).

## The doubles — [`doubles.py`](doubles.py)

Deliberately simple, **fully-typed** stand-ins. Their annotations force the gate's
type checker to verify they conform to the real ports, so a double can't silently
drift from the interface it fakes.

| Double | Fakes | Behavior |
| --- | --- | --- |
| `FakeChatModel` | `ChatModel` | Returns queued `Completion`s in order; **records** each `(conversation, tools)` it was called with, so a test can assert what the loop actually sent. Raises if it runs out — an under-scripted test fails loudly. |
| `FakeRenderer` | `Renderer` | Captures shown lines into `.lines` instead of printing. |
| `FakeInputer` | `Inputer` | Replays scripted answers, then returns `None` (EOF). |

`FakeChatModel` is the keystone: because the loop, phases, session, and subagents
all depend on the `ChatModel` port, scripting completions lets a test drive a full
ReAct run — tool requests, observations, nudges, stops — with zero network.

## What each layer's tests exercise

| Area | Tests | Notable technique |
| --- | --- | --- |
| Pure domain | `test_llm_messages`, `test_ledger`, `test_runtime`, `test_pricing`, `test_project_memory`, `test_context` | Direct assertions on immutable value objects and copy-on-write transitions. |
| Loop & control | `test_loop`, `test_navigator`, `test_control`, `test_progress` | Scripted `FakeChatModel` drives real phases; asserts transition table + nudge/stall grading. |
| Tools & policy | `test_tools`, `test_tool_adapters`, `test_policy`, `test_supervision` | Fail-closed approval, workspace confinement, deny-globs. |
| Multi-agent | `test_subagent`, `test_team`, `test_delegation`, `test_delegating_action`, `test_synthesis`, `test_documenter` | Delegation merges into the ledger; partial-findings recap on abort; the Scribe run-boundary path. |
| RAG & memory | `test_rag`, `test_rag_tool`, `test_memory_store`, `test_memory_service` | Pipeline with a fake embedder; JSON round-trip; brief/absorb seam. |
| Observability | `test_observability_spans`, `test_observability_phoenix` | Pure span mapping direct; the OTel boundary smoke-tested against a **real in-memory OpenTelemetry SDK**. |
| Adapters / wiring | `test_openai_provider`, `test_chat_model_port`, `test_cli`, `test_session`, `test_plan_mode`, `test_harness`, `test_events`, `test_packaging_smoke` | OpenAI encode/decode without the network; REPL with fakes; packaging import smoke. |

## Running

```sh
just test                       # uv run pytest — the whole suite
uv run pytest src/tests/test_loop.py            # one module
uv run pytest -k policy                          # by keyword
just validate                    # ruff + pyright + pytest (the full gate)
```
