"""Bridging one bus's events onto another, tagged with their source.

A subagent runs its inner loop on its *own* event bus, so its activity (model
calls, tool use, no-progress nudges, guard stops) never reaches the principal's
bus -- which is where the ``AuditLogger`` and the Phoenix tracer listen. An
``EventForwarder`` subscribes to the subagent's bus and republishes each event
onto the principal's, stamping it with the emitting agent's name.

Keeping the two buses separate (rather than sharing one) preserves each
subagent's isolation and lets the forwarded copy carry ``source`` -- the
provenance a nested trace and per-agent accounting both need. The forwarder is
never subscribed to its own target, so there is no republish loop.
"""

from __future__ import annotations

from dataclasses import replace

from harness.events.bus import EventBus
from harness.events.event import Event


class EventForwarder:
        """Republishes a source bus's events onto a target bus, tagged with a name."""

        def __init__(self, target: EventBus, source: str) -> None:
                self._target = target
                self._source = source

        def handle(self, event: Event) -> None:
                self._target.publish(replace(event, source=self._source))
