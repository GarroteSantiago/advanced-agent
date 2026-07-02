"""The subagent team for the repo-analysis use case.

Builds the five role-scoped subagents with their distinct tool sets (the spec's
"different tools/permissions per subagent") and registers them for the principal
to delegate to. They share the principal's model and approver, so a subagent's
mutating tool (the Tester's ``run_command``) is gated by the same policy.
"""

from __future__ import annotations

from pathlib import Path

from agent.rag_tool import RagSearchTool, RetrievalLog
from agent.subagent import Subagent
from harness.delegation import SubagentRegistry
from harness.events import EventBus
from harness.tools import (
        Approver,
        CompositeApprover,
        PolicyConfig,
        PolicyVerifier,
        ToolInterface,
)
from harness.tools.adapters import (
        ListFilesTool,
        ReadFileTool,
        RunCommandTool,
        WebSearchTool,
        WriteFileTool,
)
from llm import ChatModel
from prompts import (
        EXPLORER_PROMPT,
        IMPLEMENTER_PROMPT,
        RESEARCHER_PROMPT,
        REVIEWER_PROMPT,
        SCRIBE_PROMPT,
        TESTER_PROMPT,
)
from rag import Retriever

_DEFAULT_DOCS_DIR = Path("docs/analysis")


def _scribe_approver(docs_dir: Path, base: Approver | None) -> Approver:
        """Confine the Scribe's writes to ``docs_dir`` (fail-closed), then defer to
        whatever approver the rest of the team uses. First deny wins, so a write
        outside the documentation folder is refused before any other check runs.
        """
        confinement = PolicyVerifier(PolicyConfig(workspace=docs_dir))
        chain: list[Approver] = [confinement]
        if base is not None:
                chain.append(base)
        return CompositeApprover(chain)


def build_subagents(
        model: ChatModel,
        approver: Approver | None = None,
        retriever: Retriever | None = None,
) -> SubagentRegistry:
        # The Researcher gets rag_search (RAG-first) when a retriever is available,
        # always with web_search as fallback. Its RetrievalLog + bus carry retrieved
        # sources into its report -> the shared ledger.
        research_tools: list[ToolInterface] = [WebSearchTool()]
        research_bus: EventBus | None = None
        research_log: RetrievalLog | None = None
        if retriever is not None:
                research_log = RetrievalLog()
                research_bus = EventBus()
                research_tools = [RagSearchTool(retriever, research_log, research_bus), WebSearchTool()]

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
                                description="Look up framework/ecosystem documentation (RAG, then web).",
                                system_prompt=RESEARCHER_PROMPT,
                                model=model,
                                tools=research_tools,
                                approver=approver,
                                event_bus=research_bus,
                                retrieval_log=research_log,
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


def build_scribe(
        model: ChatModel,
        approver: Approver | None = None,
        docs_dir: Path = _DEFAULT_DOCS_DIR,
) -> Subagent:
        """The Scribe: the only writer, confined to ``docs_dir``.

        Deliberately *not* part of ``build_subagents`` -- the principal does not
        delegate to it mid-run (that left the writer under-fed). Instead the app
        invokes it at the run boundary via ``Documenter`` with the whole ledger,
        so it reliably gets every agent's findings and writes one file per agent.
        """
        return Subagent(
                name="scribe",
                description="Document the collected findings into the docs folder, one file per agent.",
                system_prompt=f"{SCRIBE_PROMPT}\n\nThe documentation folder is: {docs_dir}",
                model=model,
                tools=[WriteFileTool(), ListFilesTool()],
                approver=_scribe_approver(docs_dir, approver),
                task_description="The findings to document, grouped per agent.",
        )
