"""What a subagent hands back to the principal agent.

``SubagentReport`` is the bridge between a subagent's private run and the shared
``TaskLedger``: the delegating action phase folds these fields into the ledger
(as a ``SubagentResult`` plus merged sources/files/observations), which is how
the spec's "estado compartido" comes to record subagent work.
"""

from __future__ import annotations

from dataclasses import dataclass

from harness.runtime.ledger import Source


@dataclass(frozen=True, slots=True)
class SubagentReport:
        """An immutable summary of one subagent's contribution."""

        agent: str
        output: str
        succeeded: bool = True
        sources: tuple[Source, ...] = ()
        modified_files: tuple[str, ...] = ()
        observations: tuple[str, ...] = ()

        @classmethod
        def completed(cls, agent: str, output: str) -> SubagentReport:
                return cls(agent=agent, output=output, succeeded=True)

        @classmethod
        def failed(cls, agent: str, output: str) -> SubagentReport:
                return cls(agent=agent, output=output, succeeded=False)
