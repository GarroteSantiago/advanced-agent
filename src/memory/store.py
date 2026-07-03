"""Persistence for project memory: a port and a filesystem adapter.

``MemoryStore`` is the port (onion boundary); ``JsonMemoryStore`` is the
filesystem adapter, one JSON file per project under a base directory -- matching
the ``rag`` store's ``save``/``load`` + JSON convention. Loading an unknown
project yields an empty memory, so callers never special-case "first run".
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Protocol

from memory.project_memory import MemoryCategory, ProjectMemory

_UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")


class MemoryStore(Protocol):
        """Loads and persists a project's memory, keyed by a project identifier."""

        def load(self, project_id: str) -> ProjectMemory: ...

        def save(self, project_id: str, memory: ProjectMemory) -> None: ...


class JsonMemoryStore:
        """Stores each project's memory as one JSON file under ``directory``."""

        def __init__(self, directory: Path) -> None:
                self._directory = directory

        def load(self, project_id: str) -> ProjectMemory:
                path = self._path(project_id)
                if not path.exists():
                        return ProjectMemory.empty()
                payload = json.loads(path.read_text(encoding="utf-8"))
                memory = ProjectMemory.empty()
                for item in payload:
                        memory = self._rehydrate(memory, item)
                return memory

        def save(self, project_id: str, memory: ProjectMemory) -> None:
                self._directory.mkdir(parents=True, exist_ok=True)
                payload = [
                        {"category": entry.category.value, "content": entry.content}
                        for entry in memory.entries()
                ]
                self._path(project_id).write_text(json.dumps(payload, indent=2), encoding="utf-8")

        def _rehydrate(self, memory: ProjectMemory, item: dict[str, str]) -> ProjectMemory:
                """Fold one persisted record back through the aggregate's own invariant.

                Reuses ``remember`` rather than reconstructing entries directly, so the
                domain stays the single arbiter of what a valid entry is; unknown or
                malformed categories are skipped rather than crashing a load.
                """
                try:
                        category = MemoryCategory(item["category"])
                except (KeyError, ValueError):
                        return memory
                return memory.remember(category, item.get("content", ""))

        def _path(self, project_id: str) -> Path:
                slug = _UNSAFE.sub("_", project_id).strip("_") or "default"
                return self._directory / f"{slug}.json"
