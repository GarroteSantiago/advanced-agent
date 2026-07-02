"""The subagent team for the repo-analysis use case.

Builds the five role-scoped subagents with their distinct tool sets (the spec's
"different tools/permissions per subagent") and registers them for the principal
to delegate to. They share the principal's model and approver, so a subagent's
mutating tool (the Tester's ``run_command``) is gated by the same policy.
"""

from __future__ import annotations

from agent.subagent import Subagent
from harness.delegation import SubagentRegistry
from harness.tools import Approver
from harness.tools.adapters import (
        ListFilesTool,
        ReadFileTool,
        RunCommandTool,
        WebSearchTool,
)
from llm import ChatModel
from prompts import (
        EXPLORER_PROMPT,
        IMPLEMENTER_PROMPT,
        RESEARCHER_PROMPT,
        REVIEWER_PROMPT,
        TESTER_PROMPT,
)


def build_subagents(model: ChatModel, approver: Approver | None = None) -> SubagentRegistry:
        return SubagentRegistry(
                [
                        Subagent(
                                name="explore",
                                description=(
                                        "Understand the repository: structure, architecture, "
                                        "dependencies, conventions, and relevant files."
                                ),
                                system_prompt=EXPLORER_PROMPT,
                                model=model,
                                tools=[ReadFileTool(), ListFilesTool()],
                                approver=approver,
                                task_description="What to explore or understand about the repository.",
                        ),
                        Subagent(
                                name="research",
                                description="Look up framework/ecosystem documentation on the web.",
                                system_prompt=RESEARCHER_PROMPT,
                                model=model,
                                tools=[WebSearchTool()],
                                approver=approver,
                                task_description="What to research; be specific about the framework/topic.",
                        ),
                        Subagent(
                                name="implement",
                                description="Propose code changes or fixes as text; never applies them.",
                                system_prompt=IMPLEMENTER_PROMPT,
                                model=model,
                                tools=[ReadFileTool()],
                                approver=approver,
                                task_description="The change or fix to propose, with enough context.",
                        ),
                        Subagent(
                                name="test",
                                description="Run the repository's build, tests, or lint to gather evidence.",
                                system_prompt=TESTER_PROMPT,
                                model=model,
                                tools=[ReadFileTool(), RunCommandTool()],
                                approver=approver,
                                task_description="Which checks to run (tests, build, lint).",
                        ),
                        Subagent(
                                name="review",
                                description="Check that the findings answer the user's request.",
                                system_prompt=REVIEWER_PROMPT,
                                model=model,
                                tools=[ReadFileTool()],
                                approver=approver,
                                task_description="What to review and against which request.",
                        ),
                ]
        )
