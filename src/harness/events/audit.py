"""An event handler that records the event stream for inspection."""

from __future__ import annotations

from collections.abc import Sequence

from harness.events.event import Event


class AuditLogger:
        """Records every event it handles, in order, as an immutable trail.

        This is the minimal observability sink: later increments can add a
        handler that forwards the same stream to Langfuse/Phoenix without
        touching the core.
        """

        def __init__(self) -> None:
                self._events: list[Event] = []

        def handle(self, event: Event) -> None:
                self._events.append(event)

        def records(self) -> Sequence[Event]:
                return tuple(self._events)
