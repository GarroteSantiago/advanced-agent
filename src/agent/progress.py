"""Live progress display: turns the event stream into terminal activity lines.

``ProgressView`` is an ``EventHandler`` subscribed to the session's bus. It shows
what the agent is doing as it happens, rendering through the ``Renderer`` port so
it stays testable and never touches stdout directly. Model calls, tool calls, and
guard trips are always shown; ``verbose`` adds phase- and cycle-level detail.
"""

from __future__ import annotations

from collections.abc import Mapping

from agent.interaction import Renderer
from harness.events import (
        CycleCompleted,
        Event,
        GuardTripped,
        LoopStopped,
        ModelCalled,
        PhaseCompleted,
        PhaseStarted,
        ToolInvoked,
        ToolObserved,
)


def _summarize(arguments: Mapping[str, object], *, limit: int = 40) -> str:
        parts: list[str] = []
        for key, value in arguments.items():
                text = str(value).replace("\n", " ")
                if len(text) > limit:
                        text = text[:limit] + "…"
                parts.append(f"{key}={text}")
        return ", ".join(parts)


class ProgressView:
        """Renders the agent's live activity. ``verbose`` is a public toggle."""

        def __init__(self, renderer: Renderer, *, verbose: bool = False) -> None:
                self._renderer = renderer
                self.verbose = verbose

        def handle(self, event: Event) -> None:
                match event:
                        case ModelCalled():
                                self._renderer.show("  · thinking…")
                        case ToolInvoked(tool_name=name, arguments=args):
                                self._renderer.show(f"  → {name}({_summarize(args)})")
                        case ToolObserved(tool_name=name, ok=ok):
                                self._renderer.show(f"    {'✓' if ok else '✗'} {name}")
                        case GuardTripped(reason=reason):
                                self._renderer.show(f"  ⚠ {reason}")
                        case PhaseStarted(phase=phase) if self.verbose:
                                self._renderer.show(f"  [phase {phase} ▶]")
                        case PhaseCompleted(phase=phase) if self.verbose:
                                self._renderer.show(f"  [phase {phase} ✓]")
                        case CycleCompleted(iteration=count) if self.verbose:
                                self._renderer.show(f"  [{count} model call(s) so far]")
                        case LoopStopped(reason=reason) if self.verbose:
                                self._renderer.show(f"  [loop stopped: {reason}]")
                        case _:
                                pass
