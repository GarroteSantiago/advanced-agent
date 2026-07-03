"""The run-boundary seam between a run and its project's persistent memory.

``ProjectMemoryService`` is deliberately the *only* place that knows both a
finished run (``ExecutionResult``) and the memory store: it briefs a run from
memory before it starts and absorbs the run's ledger afterwards. Keeping this at
the composition boundary is why ``ContextManager`` can stay a pure, stateless
windowing projection -- memory is injected once as a briefing, not re-derived
every reason turn.

Capture is deterministic and model-free: the run's ``TaskLedger`` and final
report map straight onto memory entries. It fills the coarse ``SUMMARY``/``FILE``
buckets; sorting learnings into the finer buckets (architecture, dependencies,
commands, conventions, decisions, bugs) is the model-*digest* seam noted on
``ProjectMemory`` -- a future ``absorb`` could run one tool-less turn to do it.
"""

from __future__ import annotations

from harness.runtime import ExecutionResult
from memory.project_memory import MemoryCategory, ProjectMemory
from memory.store import MemoryStore


class ProjectMemoryService:
        """Briefs a run from a project's memory and absorbs its result back."""

        def __init__(self, store: MemoryStore) -> None:
                self._store = store

        def briefing(self, project_id: str) -> str:
                """The stored memory rendered for context injection ("" if none)."""
                return self._store.load(project_id).brief()

        def absorb(self, project_id: str, result: ExecutionResult) -> ProjectMemory:
                """Fold a finished run's durable findings into the project's memory.

                Records each subagent's summary and the final report (both are §2
                "summaries") plus any files the run touched, then persists. Returns
                the updated memory so callers can inspect or brief on it immediately.
                """
                memory = self._store.load(project_id)
                ledger = result.ledger
                for subagent in ledger.subagent_results():
                        memory = memory.remember(
                                MemoryCategory.SUMMARY, f"[{subagent.agent}] {subagent.summary}"
                        )
                if result.succeeded() and result.final_output:
                        memory = memory.remember(MemoryCategory.SUMMARY, result.final_output)
                for path in ledger.modified_files():
                        memory = memory.remember(MemoryCategory.FILE, path)
                self._store.save(project_id, memory)
                return memory
