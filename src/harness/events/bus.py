"""Synchronous in-process event bus.

Kept deliberately simple: publishing is a synchronous fan-out to subscribed
handlers. A ``Subscription`` is an autonomous object that knows how to detach
its handler, so callers never reach into the bus's handler list.
"""

from __future__ import annotations

from collections.abc import Callable

from harness.events.event import Event
from harness.events.handler import EventHandler


class Subscription:
        """A live link between a handler and a bus, cancellable exactly once."""

        def __init__(self, cancel: Callable[[], None]) -> None:
                self._cancel = cancel
                self._active = True

        @property
        def active(self) -> bool:
                return self._active

        def cancel(self) -> None:
                if self._active:
                        self._cancel()
                        self._active = False


class EventBus:
        """Routes published events to subscribed handlers."""

        def __init__(self) -> None:
                self._handlers: list[EventHandler] = []

        def subscribe(self, handler: EventHandler) -> Subscription:
                self._handlers.append(handler)
                return Subscription(lambda: self._handlers.remove(handler))

        def publish(self, event: Event) -> None:
                # Iterate a snapshot so a handler may unsubscribe mid-dispatch.
                for handler in tuple(self._handlers):
                        handler.handle(event)
