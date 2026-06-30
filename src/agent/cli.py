"""Interactive chat CLI: the outer loop of the basic-TP agent.

Reads a user message, runs one ReAct turn through the ``Session`` (which keeps
history), shows the answer, and waits for the next message. ``/plan`` and
``/supervise`` toggle the two modes between turns.

All user I/O goes through the ``Renderer``/``Inputer`` ports, so this module --
and the console confirmer/reviewer below -- never call ``print``/``input``
directly. That keeps the REPL testable with fakes.
"""

from __future__ import annotations

from agent.interaction import Inputer, Renderer
from agent.planning import ApprovePlan, PlanMode, PlanReview, RejectPlan, RevisePlan
from agent.progress import ProgressView
from agent.session import Session
from harness.tools import (
        Approver,
        CompositeApprover,
        PolicyConfig,
        PolicyVerifier,
        SupervisionPolicy,
)
from harness.tools.adapters import (
        ListFilesTool,
        ReadFileTool,
        RunCommandTool,
        WebSearchTool,
        WriteFileTool,
)
from harness.tools.request import ToolRequest
from llm import ChatModel

HELP = (
        "commands: /plan (toggle plan mode), /supervise (toggle supervision), "
        "/verbose (toggle detail), /help, /exit"
)

SYSTEM_PROMPT = (
        "You are a coding agent. Use the available tools to inspect and modify the "
        "project, run commands, and search the web. When the task is done, answer "
        "without calling tools."
)


class ConsoleConfirmer:
        """Asks the user to confirm a mutating action, via the I/O ports."""

        def __init__(self, inputer: Inputer) -> None:
                self._inputer = inputer

        async def confirm(self, request: ToolRequest) -> bool:
                answer = self._inputer.read(
                        f"  [supervise] allow {request.tool_name}({dict(request.arguments)})? [y/N] "
                )
                return answer is not None and answer.strip().lower() in ("y", "yes")


class ConsoleReviewer:
        """Shows the user a plan and reads their verdict, via the I/O ports."""

        def __init__(self, renderer: Renderer, inputer: Inputer) -> None:
                self._renderer = renderer
                self._inputer = inputer

        async def review(self, plan: str) -> PlanReview:
                self._renderer.show("\n--- proposed plan ---\n" + plan + "\n---------------------")
                answer = (self._inputer.read("  approve / reject / revise? [a/r/v] ") or "").strip().lower()
                if answer.startswith("a"):
                        return ApprovePlan()
                if answer.startswith("v"):
                        return RevisePlan((self._inputer.read("  your feedback: ") or "").strip())
                return RejectPlan()


def build_session(
        model: ChatModel,
        *,
        renderer: Renderer,
        inputer: Inputer,
        policy: PolicyConfig | None = None,
) -> tuple[Session, SupervisionPolicy, PlanMode, ProgressView]:
        """Wire a Session with all five tools, both interactive modes (off), and
        a live progress view subscribed to the session's events.

        If a ``policy`` is given, its guardrails are checked before supervision.
        """
        confirmer = ConsoleConfirmer(inputer)
        supervision = SupervisionPolicy(confirmer)
        plan_mode = PlanMode(ConsoleReviewer(renderer, inputer))

        approver: Approver = supervision
        if policy is not None:
                approver = CompositeApprover([PolicyVerifier(policy, confirmer), supervision])

        session = Session(
                model,
                tools=[
                        ReadFileTool(),
                        WriteFileTool(),
                        RunCommandTool(),
                        ListFilesTool(),
                        WebSearchTool(),
                ],
                approver=approver,
                plan_mode=plan_mode,
                system_prompt=SYSTEM_PROMPT,
        )

        progress = ProgressView(renderer)
        session.events.subscribe(progress)
        return session, supervision, plan_mode, progress


async def run_chat(
        session: Session,
        *,
        supervision: SupervisionPolicy,
        plan_mode: PlanMode,
        progress: ProgressView,
        renderer: Renderer,
        inputer: Inputer,
) -> None:
        renderer.show("advanced-agent chat. " + HELP)
        while True:
                line = inputer.read("\nyou> ")
                if line is None:
                        break
                message = line.strip()
                if not message:
                        continue
                if message in ("/exit", "/quit"):
                        break
                if message == "/help":
                        renderer.show(HELP)
                        continue
                if message == "/plan":
                        plan_mode.enabled = not plan_mode.enabled
                        renderer.show(f"  plan mode {'on' if plan_mode.enabled else 'off'}")
                        continue
                if message == "/supervise":
                        supervision.enabled = not supervision.enabled
                        renderer.show(f"  supervision {'on' if supervision.enabled else 'off'}")
                        continue
                if message == "/verbose":
                        progress.verbose = not progress.verbose
                        renderer.show(f"  verbose {'on' if progress.verbose else 'off'}")
                        continue

                result = await session.ask(message)
                renderer.show("\nagent> " + (result.final_output or "(no answer)"))
                footer = f"  [{result.metadata.iterations} iteration(s) | {result.stop_reason or 'done'}]"
                renderer.show(footer)
