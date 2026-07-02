"""A specialized subagent: a constrained agent the principal can delegate to.

Each ``Subagent`` runs its *own* ReAct loop (built from the shared assembly)
over a restricted tool set with its own role prompt and approver -- the concrete
realization of the spec's "each subagent may have different tools and
permissions". It implements the ``Delegate`` port, so the principal can render
it into its catalog and hand it a task via an ordinary tool call.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from agent.rag_tool import RetrievalLog
from harness.assembly import build_agent_loop
from harness.control import Controller, IterationLimiter
from harness.delegation import SubagentReport
from harness.events import EventBus
from harness.runtime import AgentExecutionContext
from harness.tools import Approver, ToolInterface, ToolRegistry
from llm import ChatModel, Conversation, Message


class Subagent:
        """A role-scoped agent that runs on delegation and reports back."""

        def __init__(
                self,
                *,
                name: str,
                description: str,
                system_prompt: str,
                model: ChatModel,
                tools: Iterable[ToolInterface] = (),
                approver: Approver | None = None,
                event_bus: EventBus | None = None,
                retrieval_log: RetrievalLog | None = None,
                max_iterations: int = 8,
                task_description: str = "The task for this subagent to carry out.",
        ) -> None:
                self._name = name
                self._description = description
                self._prompt = system_prompt
                self._task_description = task_description
                self._retrieval_log = retrieval_log

                registry = ToolRegistry()
                for tool in tools:
                        registry.register(tool)
                controller = Controller([IterationLimiter(max_iterations)])
                self._loop = build_agent_loop(
                        model=model,
                        registry=registry,
                        controller=controller,
                        event_bus=event_bus or EventBus(),
                        approver=approver,
                )

        @property
        def name(self) -> str:
                return self._name

        @property
        def description(self) -> str:
                return self._description

        def parameters(self) -> Mapping[str, object]:
                return {
                        "type": "object",
                        "properties": {
                                "task": {"type": "string", "description": self._task_description}
                        },
                        "required": ["task"],
                }

        async def delegate(self, task: str) -> SubagentReport:
                if self._retrieval_log is not None:
                        self._retrieval_log.drain()  # discard any stale sources before this run

                conversation = (
                        Conversation.empty()
                        .with_message(Message.system(self._prompt))
                        .with_message(Message.user(task))
                )
                context = AgentExecutionContext.for_task(self._name, conversation, request=task)
                result = await self._loop.run(context)

                sources = self._retrieval_log.drain() if self._retrieval_log is not None else ()
                output = result.final_output or ""
                if result.succeeded():
                        return SubagentReport(agent=self._name, output=output, sources=sources)
                return SubagentReport(
                        agent=self._name,
                        output=output or (result.stop_reason or "subagent did not complete"),
                        succeeded=False,
                        sources=sources,
                )
