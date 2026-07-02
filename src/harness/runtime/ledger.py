"""The shared task ledger: what the agents learn, decide, and touch.

``TaskLedger`` is the structured task-state the spec mandates (``estado
compartido``): beyond the raw conversation it records the original request, the
progress made, each subagent's result, the sources consulted, the files
modified, and the relevant observations. It is immutable and copy-on-write like
``AgentExecutionContext`` (which holds one), so recording a fact never mutates a
ledger another collaborator is reading -- the property that lets the principal
agent and its subagents share one ledger safely in a later increment.

``Source`` carries an ``Origin`` tag so the ledger can answer the spec's
"differentiate repo vs memory vs RAG vs web vs inference" requirement: the
provenance of a fact travels with the fact, not in a comment.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from enum import Enum


class Origin(Enum):
        """Where a consulted fact came from."""

        REPO = "repo"
        MEMORY = "memory"
        RAG = "rag"
        WEB = "web"
        INFERENCE = "inference"


@dataclass(frozen=True, slots=True)
class Source:
        """A provenance-tagged reference the agents relied on."""

        origin: Origin
        reference: str
        note: str = ""

        @classmethod
        def from_repo(cls, reference: str, note: str = "") -> Source:
                return cls(Origin.REPO, reference, note)

        @classmethod
        def from_memory(cls, reference: str, note: str = "") -> Source:
                return cls(Origin.MEMORY, reference, note)

        @classmethod
        def from_rag(cls, reference: str, note: str = "") -> Source:
                return cls(Origin.RAG, reference, note)

        @classmethod
        def from_web(cls, reference: str, note: str = "") -> Source:
                return cls(Origin.WEB, reference, note)

        @classmethod
        def inferred(cls, note: str = "") -> Source:
                return cls(Origin.INFERENCE, "", note)


@dataclass(frozen=True, slots=True)
class SubagentResult:
        """The outcome a subagent handed back to the principal agent."""

        agent: str
        summary: str
        succeeded: bool = True

        @classmethod
        def completed(cls, agent: str, summary: str) -> SubagentResult:
                return cls(agent, summary, succeeded=True)

        @classmethod
        def failed(cls, agent: str, summary: str) -> SubagentResult:
                return cls(agent, summary, succeeded=False)


@dataclass(frozen=True, slots=True)
class TaskLedger:
        """Immutable, copy-on-write record of the shared task state."""

        _original_request: str
        _progress: tuple[str, ...] = ()
        _subagent_results: tuple[SubagentResult, ...] = ()
        _sources: tuple[Source, ...] = ()
        _modified_files: tuple[str, ...] = ()
        _observations: tuple[str, ...] = ()

        @classmethod
        def for_request(cls, request: str) -> TaskLedger:
                return cls(_original_request=request)

        # --- queries -------------------------------------------------------
        def original_request(self) -> str:
                return self._original_request

        def progress(self) -> Sequence[str]:
                return self._progress

        def subagent_results(self) -> Sequence[SubagentResult]:
                return self._subagent_results

        def sources_consulted(self) -> Sequence[Source]:
                return self._sources

        def modified_files(self) -> Sequence[str]:
                return self._modified_files

        def observations(self) -> Sequence[str]:
                return self._observations

        # --- transitions (copy-on-write) -----------------------------------
        def with_progress(self, note: str) -> TaskLedger:
                return replace(self, _progress=(*self._progress, note))

        def with_subagent_result(self, result: SubagentResult) -> TaskLedger:
                return replace(self, _subagent_results=(*self._subagent_results, result))

        def with_source(self, source: Source) -> TaskLedger:
                return replace(self, _sources=(*self._sources, source))

        def with_modified_file(self, path: str) -> TaskLedger:
                if path in self._modified_files:
                        return self
                return replace(self, _modified_files=(*self._modified_files, path))

        def with_observation(self, note: str) -> TaskLedger:
                return replace(self, _observations=(*self._observations, note))
