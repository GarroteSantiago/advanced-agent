"""The documentation run-boundary seam.

``Documenter`` invokes the Scribe *after* a run with the whole shared ledger, so
the writer reliably receives every agent's findings and can write one file per
agent. This is the deterministic alternative to letting the principal delegate
to the Scribe mid-run, where the coordinator tended to under-feed it (passing
only one agent's findings). It mirrors ``ProjectMemoryService`` as an app-level
seam: the harness stays generic, and only this layer knows about the Scribe.
"""

from __future__ import annotations

from agent.subagent import Subagent
from harness.delegation import SubagentReport
from harness.runtime import TaskLedger


class Documenter:
        """Drives the Scribe to persist a finished run's findings to the docs folder."""

        def __init__(self, scribe: Subagent) -> None:
                self._scribe = scribe

        async def document(self, ledger: TaskLedger) -> SubagentReport:
                """Hand every agent's findings to the Scribe to write, one file per agent.

                A run with no subagent results writes nothing (there is nothing to
                document) and reports so, rather than invoking the Scribe for an
                empty task.
                """
                if not ledger.subagent_results():
                        return SubagentReport.completed("scribe", "no findings to document")
                return await self._scribe.delegate(_assemble(ledger))


def _assemble(ledger: TaskLedger) -> str:
        header = (
                "Document the following analysis findings. Write ONE file per agent below "
                "-- a single file holding that agent's findings -- into the documentation "
                f"folder.\n\nOriginal request: {ledger.original_request()}\n\n"
        )
        blocks = [
                f"=== agent: {result.agent} ({'complete' if result.succeeded else 'partial'}) ===\n"
                f"{result.summary}"
                for result in ledger.subagent_results()
        ]
        return header + "\n\n".join(blocks)
