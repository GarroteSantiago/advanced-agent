"""Tests for the run-boundary Documenter that drives the Scribe."""

from agent.documenter import Documenter
from agent.team import build_scribe
from harness.runtime.ledger import SubagentResult, TaskLedger
from llm import Completion, ToolCall
from tests.doubles import FakeChatModel


def _ledger_with(*results: SubagentResult) -> TaskLedger:
        ledger = TaskLedger.for_request("analyze the repo")
        for result in results:
                ledger = ledger.with_subagent_result(result)
        return ledger


async def test_documenter_has_the_scribe_write_one_file_per_agent(tmp_path) -> None:
        docs = tmp_path / "docs"
        model = FakeChatModel(
                [
                        Completion(
                                tool_calls=(
                                        ToolCall(
                                                id="w1",
                                                name="write_file",
                                                arguments={
                                                        "path": str(docs / "explore.md"),
                                                        "content": "explore info",
                                                },
                                        ),
                                )
                        ),
                        Completion(
                                tool_calls=(
                                        ToolCall(
                                                id="w2",
                                                name="write_file",
                                                arguments={
                                                        "path": str(docs / "research.md"),
                                                        "content": "research info",
                                                },
                                        ),
                                )
                        ),
                        Completion(content="wrote explore.md and research.md"),
                ]
        )
        documenter = Documenter(build_scribe(model, docs_dir=docs))
        ledger = _ledger_with(
                SubagentResult.completed("explore", "found APIRouter"),
                SubagentResult.completed("research", "FastAPI conventions"),
        )

        report = await documenter.document(ledger)

        assert (docs / "explore.md").read_text(encoding="utf-8") == "explore info"
        assert (docs / "research.md").read_text(encoding="utf-8") == "research info"
        assert set(report.modified_files) == {str(docs / "explore.md"), str(docs / "research.md")}


async def test_documenter_hands_every_agents_findings_to_the_scribe(tmp_path) -> None:
        model = FakeChatModel([Completion(content="ok")])  # answers without writing
        documenter = Documenter(build_scribe(model, docs_dir=tmp_path))
        ledger = _ledger_with(
                SubagentResult.completed("explore", "MARKER-EXPLORE"),
                SubagentResult.failed("test", "MARKER-TEST"),
        )

        await documenter.document(ledger)

        sent, _ = model.calls[0]
        text = " ".join(message.content for message in sent.messages())
        assert "MARKER-EXPLORE" in text
        assert "MARKER-TEST" in text  # partial findings are documented too


async def test_documenter_writes_nothing_without_findings(tmp_path) -> None:
        documenter = Documenter(build_scribe(FakeChatModel([]), docs_dir=tmp_path))

        report = await documenter.document(TaskLedger.for_request("nothing yet"))

        assert report.modified_files == ()
        assert not list(tmp_path.glob("*"))  # the Scribe was never invoked
