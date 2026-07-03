"""The project-memory aggregate: durable knowledge about one target project.

``ProjectMemory`` is the persistent counterpart to the in-run ``TaskLedger``:
where the ledger records what *this* run learned and is discarded when the run
ends, ``ProjectMemory`` accumulates what every run learned about a given project
and survives across sessions (persisted by a ``MemoryStore``). Like the ledger
it is immutable and copy-on-write, and it is not anemic -- it knows how to
render itself as a briefing (``brief``) for injection into a later run's context.

The ``MemoryCategory`` buckets are the spec's mandated fields (architecture,
files, dependencies, commands, conventions, decisions, bugs, summaries). The
deterministic ledger-based capture currently fills the coarse ``SUMMARY``/``FILE``
buckets; a model-based *digest* that sorts learnings into the finer buckets is
the noted next seam (mirroring the ``Summarizer`` seam left in ``ContextManager``).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from enum import Enum


class MemoryCategory(Enum):
        """The kind of durable fact a memory entry records (spec §2)."""

        ARCHITECTURE = "architecture"
        FILE = "file"
        DEPENDENCY = "dependency"
        COMMAND = "command"
        CONVENTION = "convention"
        DECISION = "decision"
        BUG = "bug"
        SUMMARY = "summary"


# Human-readable section headings for ``brief``; order defines briefing order.
_HEADINGS: dict[MemoryCategory, str] = {
        MemoryCategory.ARCHITECTURE: "Architecture",
        MemoryCategory.FILE: "Files",
        MemoryCategory.DEPENDENCY: "Dependencies",
        MemoryCategory.COMMAND: "Commands",
        MemoryCategory.CONVENTION: "Conventions",
        MemoryCategory.DECISION: "Decisions",
        MemoryCategory.BUG: "Known issues",
        MemoryCategory.SUMMARY: "Summaries from earlier sessions",
}


@dataclass(frozen=True, slots=True)
class MemoryEntry:
        """A single provenance-agnostic fact, tagged with its category."""

        category: MemoryCategory
        content: str


@dataclass(frozen=True, slots=True)
class ProjectMemory:
        """Immutable, copy-on-write accumulation of what is known about a project."""

        _entries: tuple[MemoryEntry, ...] = ()

        @classmethod
        def empty(cls) -> ProjectMemory:
                return cls()

        # --- queries -------------------------------------------------------
        def is_empty(self) -> bool:
                return not self._entries

        def entries(self, category: MemoryCategory | None = None) -> Sequence[MemoryEntry]:
                if category is None:
                        return self._entries
                return tuple(entry for entry in self._entries if entry.category is category)

        def brief(self) -> str:
                """Render the memory as a briefing to inject into a later run.

                Empty categories are omitted; empty memory renders as ``""`` so a
                caller can cheaply decide whether to inject anything at all.
                """
                if self.is_empty():
                        return ""
                sections: list[str] = [
                        "# What is already known about this project (from earlier sessions)"
                ]
                for category, heading in _HEADINGS.items():
                        found = self.entries(category)
                        if not found:
                                continue
                        sections.append(f"\n## {heading}")
                        sections.extend(f"- {entry.content}" for entry in found)
                return "\n".join(sections)

        # --- transitions (copy-on-write) -----------------------------------
        def remember(self, category: MemoryCategory, content: str) -> ProjectMemory:
                """Record a fact, unless an identical one is already remembered.

                Exact-duplicate suppression keeps a project's memory from bloating
                when the same run is repeated; near-duplicates (reworded summaries)
                still accumulate -- consolidating those is the digest seam's job.
                """
                text = content.strip()
                if not text:
                        return self
                entry = MemoryEntry(category, text)
                if entry in self._entries:
                        return self
                return replace(self, _entries=(*self._entries, entry))
