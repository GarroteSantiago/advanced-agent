"""A multi-turn, mode-aware conversational agent.

``Session`` is the outer half of the basic-TP's two nested loops: it holds the
running ``Conversation`` across user turns, and on each ``ask`` runs the inner
ReAct loop seeded with the accumulated history. The inner loop ends when the
model answers without tools; the program then waits for the next ``ask``,
keeping context.
"""

from __future__ import annotations

from collections.abc import Iterable

from agent.planning import PlanMode
from harness.assembly import build_agent_loop
from harness.control import Controller, Guard, IterationLimiter
from harness.events import EventBus, EventHandler
from harness.runtime import AgentExecutionContext, ExecutionResult
from harness.tools import Approver, AutoApprover, ToolInterface, ToolRegistry
from llm import ChatModel, Conversation, Message


class Session:
        """Holds conversation state and runs one ReAct loop per user turn."""

        def __init__(
                self,
                model: ChatModel,
                *,
                tools: Iterable[ToolInterface] = (),
                guards: Iterable[Guard] = (),
                handlers: Iterable[EventHandler] = (),
                approver: Approver | None = None,
                plan_mode: PlanMode | None = None,
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
                self._approver = approver or AutoApprover()
                self._plan_mode = plan_mode

                self._conversation = Conversation.empty()
                if system_prompt is not None:
                        self._conversation = self._conversation.with_message(Message.system(system_prompt))

        @property
        def events(self) -> EventBus:
                """The session's event bus; subscribe observers before asking."""
                return self._bus

        def conversation(self) -> Conversation:
                return self._conversation

        async def ask(self, message: str, *, task_id: str = "turn") -> ExecutionResult:
                self._conversation = self._conversation.with_message(Message.user(message))

                if self._plan_mode is not None and self._plan_mode.enabled:
                        approved = await self._plan_mode.negotiate(self._model, self._conversation)
                        if approved is None:
                                rejected = AgentExecutionContext.for_task(
                                        task_id, self._conversation, request=message
                                ).aborted("user rejected the plan")
                                return ExecutionResult.from_context(rejected)
                        self._conversation = approved

                loop = build_agent_loop(
                        model=self._model,
                        registry=self._registry,
                        controller=self._controller,
                        event_bus=self._bus,
                        approver=self._approver,
                )
                result = await loop.run(
                        AgentExecutionContext.for_task(task_id, self._conversation, request=message)
                )
                self._conversation = result.conversation  # persist history across turns
                return result
