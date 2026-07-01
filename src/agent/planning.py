"""Plan mode: produce a plan and get the user's approval before acting.

When enabled, a turn first asks the model for a numbered plan (no tools), shows
it to the user via a ``PlanReviewer``, and only runs the action loop once the
plan is approved. The user may approve, reject, or send the plan back for
revision. Disabled, the agent acts directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from llm import ChatModel, Conversation, Message

PLAN_INSTRUCTION = (
        "Produce a short, numbered plan of the steps you will take to accomplish "
        "the request. Do not use any tools yet -- output only the plan."
)


class PlanReview:
        """The user's verdict on a proposed plan. Sealed."""

        __slots__ = ()


class ApprovePlan(PlanReview):
        """Run the plan as proposed."""

        __slots__ = ()


class RejectPlan(PlanReview):
        """Abandon the turn; execute nothing."""

        __slots__ = ()


@dataclass(frozen=True, slots=True)
class RevisePlan(PlanReview):
        """Re-plan, taking the user's feedback into account."""

        feedback: str


@runtime_checkable
class PlanReviewer(Protocol):
        """Shows the user a plan and returns their verdict."""

        async def review(self, plan: str) -> PlanReview: ...


class PlanMode:
        """Negotiates a plan with the user before the action loop runs.

        ``enabled`` is a public toggle so the user can switch plan mode on/off
        between turns.
        """

        def __init__(self, reviewer: PlanReviewer, *, enabled: bool = False) -> None:
                self._reviewer = reviewer
                self.enabled = enabled

        async def negotiate(
                self, model: ChatModel, conversation: Conversation
        ) -> Conversation | None:
                """Loop plan -> review until approved or rejected.

                Returns the conversation to proceed with (the approved plan folded
                in as an assistant turn), or ``None`` if the user rejected it.
                """
                working = conversation
                while True:
                        plan = (
                                await model.complete(working.with_message(Message.user(PLAN_INSTRUCTION)))
                        ).content
                        match await self._reviewer.review(plan):
                                case ApprovePlan():
                                        return working.with_message(Message.assistant(plan))
                                case RevisePlan(feedback):
                                        working = working.with_message(
                                                Message.assistant(plan)
                                        ).with_message(Message.user(feedback))
                                case _:
                                        return None
