"""Assembles the ReAct loop from its collaborators.

The single place the phase graph is wired, shared by every composition root
(the single-shot ``Harness`` and the multi-turn ``Session``). Adding a phase or
rerouting the graph happens here.
"""

from __future__ import annotations

from harness.control import Controller
from harness.events import EventBus
from harness.loop import (
        ActionPhase,
        AgentLoop,
        Continue,
        Halt,
        Navigator,
        ObservationPhase,
        Outcome,
        ReasonPhase,
)
from harness.tools import Approver, ToolExecutor, ToolRegistry
from llm import ChatModel


def build_agent_loop(
        *,
        model: ChatModel,
        registry: ToolRegistry,
        controller: Controller,
        event_bus: EventBus,
        approver: Approver | None = None,
) -> AgentLoop:
        executor = ToolExecutor(registry, event_bus, approver)
        reason = ReasonPhase(model, registry.catalog(), event_bus)
        action = ActionPhase(executor)
        observation = ObservationPhase(controller, event_bus)
        navigator = Navigator(
                start=reason,
                transitions={
                        (reason, Outcome.TOOLS_REQUESTED): Continue(action),
                        (reason, Outcome.ANSWERED): Halt(),
                        (action, Outcome.ACTED): Continue(observation),
                        (observation, Outcome.CONTINUE): Continue(reason),
                        (observation, Outcome.DENIED): Halt(),
                },
        )
        return AgentLoop(navigator, event_bus)
