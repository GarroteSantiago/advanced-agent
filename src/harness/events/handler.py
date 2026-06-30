"""The event handler port."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from harness.events.event import Event


@runtime_checkable
class EventHandler(Protocol):
        """Anything that reacts to events published on the bus."""

        def handle(self, event: Event) -> None: ...
