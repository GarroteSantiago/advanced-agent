"""Chunking: split documents into overlapping passages for retrieval.

A ``Chunk`` is the unit that gets embedded and retrieved; it carries its source
reference so a retrieval can be attributed (the spec's "show which fragments").
The chunker is pure (no embedding, no IO), so it is trivially testable.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Chunk:
        """One retrievable passage and where it came from."""

        text: str
        source: str
        ordinal: int


@dataclass(frozen=True, slots=True)
class Chunker:
        """Splits text into overlapping character windows on paragraph bounds."""

        size: int = 900
        overlap: int = 150

        def __post_init__(self) -> None:
                if self.size <= 0:
                        raise ValueError("chunk size must be positive")
                if not 0 <= self.overlap < self.size:
                        raise ValueError("overlap must be in [0, size)")

        def chunk(self, text: str, source: str) -> list[Chunk]:
                cleaned = text.strip()
                if not cleaned:
                        return []
                step = self.size - self.overlap
                windows = [cleaned[i : i + self.size] for i in range(0, len(cleaned), step)]
                # Drop a trailing window fully contained in the previous one.
                if len(windows) >= 2 and len(cleaned) - (len(windows) - 1) * step <= self.overlap:
                        windows.pop()
                return [
                        Chunk(text=window, source=source, ordinal=index)
                        for index, window in enumerate(windows)
                ]
