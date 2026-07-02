"""The harness: a single-shot composition root.

``Harness`` wires the event bus, tool registry, and controller, and on each
``run`` assembles the loop (via ``build_agent_loop``) around a fresh context.
For multi-turn, mode-aware conversations use ``agent.Session``, which reuses the
same assembly but persists history across turns.
"""

from __future__ import annotations

from collections.abc import Iterable

from harness.assembly import build_agent_loop
from harness.control import Controller, Guard, IterationLimiter
from harness.events import EventBus, EventHandler
from harness.runtime import AgentExecutionContext, ExecutionResult
from harness.tools import ToolInterface, ToolRegistry
from llm import ChatModel, Conversation, Message


class Harness:
        """Assembles and runs the agent loop for a single task."""

        def __init__(
                self,
                model: ChatModel,
                *,
                tools: Iterable[ToolInterface] = (),
                guards: Iterable[Guard] = (),
                handlers: Iterable[EventHandler] = (),
                max_iterations: int = 10,
                system_prompt: str | None = None,
        ) -> None:
                self._model = model
                self._bus = EventBus()
                for handler in handlers:
                        self._bus.subscribe(handler)

                self._registry = ToolRegistry()
                for tool in tools:
                        self._registry.register(tool)

                self._controller = Controller([IterationLimiter(max_iterations), *guards])
                self._system_prompt = system_prompt

        @property
        def events(self) -> EventBus:
                """The run's event bus; subscribe observers here before running."""
                return self._bus

        async def run(self, task: str, *, task_id: str = "task") -> ExecutionResult:
                loop = build_agent_loop(
                        model=self._model,
                        registry=self._registry,
                        controller=self._controller,
                        event_bus=self._bus,
                )
                return await loop.run(
                        AgentExecutionContext.for_task(task_id, self._seed(task), request=task)
                )

        def _seed(self, task: str) -> Conversation:
                conversation = Conversation.empty()
                if self._system_prompt is not None:
                        conversation = conversation.with_message(Message.system(self._system_prompt))
                return conversation.with_message(Message.user(task))
