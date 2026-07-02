"""Reproducible live demo: analyse a repo with the advanced agent, print evidence.

This is the committed replacement for the ephemeral scratchpad drivers. It runs
one repo-analysis task through the principal coordinator against a target repo,
then prints an evidence report that maps onto the TP's gradable sections:

  * multi-agent delegation (subagent results in the shared ledger)        -- §1/§2
  * RAG (sources tagged ``rag`` + documents-retrieved events)             -- §3
  * context/loop behaviour (no-progress nudges, partial-findings reports)  -- §4
  * observability fields (tokens, latency, cost per model call)            -- §6

Run it from the repository root (so ``.env`` and ``data/rag_index`` resolve):

    python scripts/analyze_repo.py [TARGET_DIR]

``TARGET_DIR`` defaults to ``scripts/sample_app`` (a small committed FastAPI
project). Requires ``OPENAI_API_KEY`` in ``.env`` -- this spends API tokens.

Note: model/env/RAG wiring is reused from ``main`` rather than duplicated; the
``import main`` needs the repository root on ``sys.path``, hence the insert below.
"""

from __future__ import annotations

import asyncio
import os
import sys
from collections import Counter
from pathlib import Path
from typing import TextIO

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import main  # noqa: E402
from agent.cli import build_session  # noqa: E402
from agent.interaction import ConsoleRenderer, Renderer  # noqa: E402
from agent.session import Session  # noqa: E402
from harness.events import (  # noqa: E402
        AuditLogger,
        DocumentsRetrieved,
        GuardTripped,
        ModelCompleted,
        StrategyNudged,
        ToolInvoked,
)
from harness.runtime import ExecutionResult  # noqa: E402

_DEFAULT_TARGET = "scripts/sample_app"


class _SilentInputer:
        """A non-interactive ``Inputer``: never prompts (returns EOF).

        Supervision and plan mode are off in ``build_session``, so this is never
        consulted; it exists only to satisfy the port for a headless run.
        """

        def read(self, prompt: str) -> str | None:
                return None


def _task(target: str) -> str:
        return (
                f"Analyse the FastAPI project located at {target}. Produce a concise report "
                "covering: (1) the architecture and how routes are wired, (2) the dependencies, "
                "(3) any risks or issues, and (4) useful commands to run it and its tests. "
                "Delegate to your subagents: have the Explorer map the files, the Researcher "
                "confirm the relevant FastAPI conventions, and the Tester inspect the test suite."
        )


def _report(renderer: Renderer, result: ExecutionResult, audit: AuditLogger) -> None:
        show = renderer.show
        ledger = result.ledger

        show("\n================ EVIDENCE REPORT ================")
        show(f"succeeded: {result.succeeded()}")
        show(f"iterations: {result.metadata.iterations}")
        show(f"stop reason: {result.stop_reason or 'done'}")

        show("\n--- subagents (§1/§2) ---")
        for entry in ledger.subagent_results():
                flag = "" if entry.succeeded else " [PARTIAL]"
                summary = entry.summary.replace("\n", " ")[:140]
                show(f"  {entry.agent}{flag}: {summary}")

        show("\n--- sources consulted, by origin (§2/§3) ---")
        by_origin: Counter[str] = Counter(s.origin.value for s in ledger.sources_consulted())
        for origin, count in sorted(by_origin.items()):
                show(f"  {origin}: {count}")
        if not by_origin:
                show("  (none recorded)")

        show("\n--- control & loop behaviour (§4) ---")
        nudges = [e for e in audit.records() if isinstance(e, StrategyNudged)]
        guards = [e for e in audit.records() if isinstance(e, GuardTripped)]
        partials = [r for r in ledger.subagent_results() if not r.succeeded]
        show(f"  no-progress nudges: {len(nudges)}")
        show(f"  guard stops: {len(guards)}" + (f" ({guards[-1].reason})" if guards else ""))
        show(f"  partial-findings reports: {len(partials)}")

        show("\n--- observability (§6) ---")
        completions = [e for e in audit.records() if isinstance(e, ModelCompleted)]
        retrievals = [e for e in audit.records() if isinstance(e, DocumentsRetrieved)]
        tools = [e for e in audit.records() if isinstance(e, ToolInvoked)]
        total_cost = sum(e.cost_usd for e in completions)
        total_tokens = sum(e.prompt_tokens + e.completion_tokens for e in completions)
        show(f"  model calls: {len(completions)} | tools invoked: {len(tools)} "
             f"| documents retrieved: {len(retrievals)}")
        show(f"  total tokens: {total_tokens} | estimated cost: ${total_cost:.4f}")

        show("\n================ FINAL ANSWER ================")
        show(result.final_output or "(no answer)")


def _enable_tracing(session: Session, renderer: Renderer) -> TextIO | None:
        """Attach a trace sink chosen by OBSERVABILITY; return a handle to close.

        ``phoenix`` launches the local Phoenix UI (screenshot it for §9.7).
        ``otel-file`` writes the same spans as JSON lines to OTEL_TRACE_FILE --
        a durable, headless-friendly trace artifact. Anything else: no tracing.
        """
        mode = os.environ.get("OBSERVABILITY", "").lower()
        if mode == "phoenix":
                from observability.phoenix import launch_phoenix_tracer

                session.events.subscribe(launch_phoenix_tracer())
                renderer.show("observability: Phoenix UI launched (screenshot it for evidence)")
                return None
        if mode in ("otel-file", "file"):
                from opentelemetry.sdk.trace import TracerProvider
                from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

                from observability.phoenix import PhoenixTracer

                path = os.environ.get("OTEL_TRACE_FILE", "otel-trace.jsonl")
                # Kept open across the run; closed by the caller after the report.
                handle = Path(path).open("w", encoding="utf-8")  # noqa: SIM115
                provider = TracerProvider()
                # One compact span per line (JSONL), not the default pretty print.
                exporter = ConsoleSpanExporter(out=handle, formatter=lambda s: s.to_json(indent=None) + "\n")
                provider.add_span_processor(SimpleSpanProcessor(exporter))
                session.events.subscribe(PhoenixTracer(provider.get_tracer("advanced-agent")))
                renderer.show(f"observability: OTel spans -> {path}")
                return handle
        return None


async def _run(target: str) -> None:
        main._load_dotenv()
        renderer = ConsoleRenderer()

        model = main._build_model(renderer)
        retriever = main._build_retriever(renderer)
        session, _supervision, _plan, _progress = build_session(
                model, renderer=renderer, inputer=_SilentInputer(), retriever=retriever
        )

        audit = AuditLogger()
        session.events.subscribe(audit)
        trace_handle = _enable_tracing(session, renderer)

        renderer.show(f"\nanalysing: {target}\n")
        result = await session.ask(_task(target))
        _report(renderer, result, audit)

        if trace_handle is not None:
                trace_handle.flush()
                trace_handle.close()


def main_() -> None:
        target = sys.argv[1] if len(sys.argv) > 1 else _DEFAULT_TARGET
        asyncio.run(_run(target))


if __name__ == "__main__":
        main_()
