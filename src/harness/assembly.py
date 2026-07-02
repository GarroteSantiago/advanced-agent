"""Assembles the ReAct loop from its collaborators.

The single place the phase graph is wired, shared by every composition root
(the single-shot ``Harness`` and the multi-turn ``Session``). Adding a phase or
rerouting the graph happens here.
"""

from __future__ import annotations

from harness.control import Controller
from harness.delegation import SubagentRegistry
from harness.events import EventBus
from harness.loop import (
        ActionPhase,
        AgentLoop,
        Continue,
        DelegatingActionPhase,
        Halt,
        Navigator,
        ObservationPhase,
        Outcome,
        Phase,
        ReasonPhase,
)
from harness.tools import Approver, ToolCatalog, ToolExecutor, ToolRegistry
from llm import ChatModel


def build_agent_loop(
        *,
        model: ChatModel,
        registry: ToolRegistry,
        controller: Controller,
        event_bus: EventBus,
        approver: Approver | None = None,
        subagents: SubagentRegistry | None = None,
) -> AgentLoop:
        executor = ToolExecutor(registry, event_bus, approver)
        action: Phase
        if subagents is not None:
                catalog = ToolCatalog.of_tools([*registry.tools(), *subagents.all()])
                action = DelegatingActionPhase(executor, subagents, event_bus)
        else:
                catalog = registry.catalog()
                action = ActionPhase(executor)
        reason = ReasonPhase(model, catalog, event_bus)
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
