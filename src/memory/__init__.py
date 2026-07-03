"""Persistent per-project memory (spec §2).

Durable knowledge about a *specific target project* that survives across agent
sessions -- distinct from the ``rag`` package (framework-level general knowledge)
and the in-run ``TaskLedger`` (discarded when a run ends). ``ProjectMemory`` is
the aggregate; ``MemoryStore``/``JsonMemoryStore`` persist it; and
``ProjectMemoryService`` is the run-boundary seam that briefs a run from memory
and absorbs a finished run's ledger back into it.
"""

from memory.project_memory import MemoryCategory, MemoryEntry, ProjectMemory
from memory.service import ProjectMemoryService
from memory.store import JsonMemoryStore, MemoryStore

__all__ = [
        "JsonMemoryStore",
        "MemoryCategory",
        "MemoryEntry",
        "MemoryStore",
        "ProjectMemory",
        "ProjectMemoryService",
]
