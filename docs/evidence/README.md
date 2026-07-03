# Evidence — Observability trace (§9.7)

> For the executed-task demos (§8: RAG, project memory, strategy-change/stop,
> observability) see [`task-evidence.md`](task-evidence.md). This file covers the
> observability trace specifically.

`repo-analysis.otel.jsonl` is a real OpenTelemetry trace captured from one live
run of the principal coordinator analysing `scripts/sample_app` (a small FastAPI
fixture). Each line is one finished span, exported compactly (one span per line)
by the `OBSERVABILITY=otel-file` sink in `scripts/analyze_repo.py`.

## How it was produced

```
OBSERVABILITY=otel-file \
OTEL_TRACE_FILE=docs/evidence/repo-analysis.otel.jsonl \
uv run python scripts/analyze_repo.py
```

(Requires `uv sync --extra observability` and `OPENAI_API_KEY` in `.env`.)

## What it demonstrates

The `PhoenixTracer` maps the harness event stream onto nested spans:

- **One run root** (`agent.run`) — the whole task is a single trace tree. A
  subagent's `LoopStopped` is forwarded source-tagged and must *not* close the
  root; only the principal's stop does. Verified by the count below.
- **An `llm <model>` span per model call** carrying tokens, latency, and cost.
- **A `tool <name>` span per tool call**, paired by `call_id` for real durations.
- **Per-agent attribution** via the `agent.name` attribute, sourced from the
  event's `source` tag — so subagent activity (Explorer/Researcher/Tester) is
  distinguishable from the principal's within the one tree.

## Shape of this capture

```
total spans:        59
agent.run roots:    1          # single-rooted — subagent stops do not close it
spans with parent:  58 / 59    # everything nests under the run root
by kind:            llm 27 · tool 31 · agent.run 1
agent.name:         principal 6 · explore 22 · research 18 · test 13
```
