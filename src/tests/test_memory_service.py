"""Tests for the ProjectMemoryService run-boundary seam."""

from pathlib import Path

from harness.runtime import ExecutionResult
from harness.runtime.ledger import SubagentResult, TaskLedger
from harness.runtime.metadata import ExecutionMetadata
from harness.runtime.state import ExecutionState
from llm import Conversation
from memory import JsonMemoryStore, MemoryCategory, ProjectMemory, ProjectMemoryService


def _result(
        *,
        final_output: str | None,
        state: ExecutionState = ExecutionState.COMPLETED,
        subagents: tuple[SubagentResult, ...] = (),
        modified: tuple[str, ...] = (),
) -> ExecutionResult:
        ledger = TaskLedger.for_request("analyze the repo")
        for subagent in subagents:
                ledger = ledger.with_subagent_result(subagent)
        for path in modified:
                ledger = ledger.with_modified_file(path)
        return ExecutionResult(
                final_output=final_output,
                state=state,
                metadata=ExecutionMetadata(task_id="t-1"),
                conversation=Conversation.empty(),
                ledger=ledger,
        )


class _FakeStore:
        """In-memory MemoryStore double."""

        def __init__(self) -> None:
                self.saved: dict[str, ProjectMemory] = {}

        def load(self, project_id: str) -> ProjectMemory:
                return self.saved.get(project_id, ProjectMemory.empty())

        def save(self, project_id: str, memory: ProjectMemory) -> None:
                self.saved[project_id] = memory


def test_briefing_is_blank_for_an_unknown_project() -> None:
        assert ProjectMemoryService(_FakeStore()).briefing("unknown") == ""


def test_absorb_records_subagent_findings_and_the_final_report() -> None:
        store = _FakeStore()
        service = ProjectMemoryService(store)
        result = _result(
                final_output="The project is a FastAPI app.",
                subagents=(SubagentResult.completed("explore", "found APIRouter in app/routers"),),
        )

        memory = service.absorb("proj", result)

        summaries = [e.content for e in memory.entries(MemoryCategory.SUMMARY)]
        assert "[explore] found APIRouter in app/routers" in summaries
        assert "The project is a FastAPI app." in summaries
        assert store.saved["proj"] is memory  # persisted


def test_absorb_records_touched_files() -> None:
        memory = ProjectMemoryService(_FakeStore()).absorb(
                "proj", _result(final_output=None, modified=("app/main.py",))
        )
        assert [e.content for e in memory.entries(MemoryCategory.FILE)] == ["app/main.py"]


def test_absorb_ignores_the_report_of_an_aborted_run() -> None:
        memory = ProjectMemoryService(_FakeStore()).absorb(
                "proj", _result(final_output="half an answer", state=ExecutionState.ABORTED)
        )
        assert memory.is_empty()  # no final report recorded when the run did not complete


def test_absorb_then_brief_recalls_across_sessions(tmp_path: Path) -> None:
        # Session one absorbs; a fresh service over the same store briefs from it.
        store_dir = tmp_path / "memory"
        first = ProjectMemoryService(JsonMemoryStore(store_dir))
        first.absorb(
                "proj",
                _result(
                        final_output="FastAPI + pytest.",
                        subagents=(SubagentResult.completed("test", "2 tests pass via pytest -q"),),
                ),
        )

        second = ProjectMemoryService(JsonMemoryStore(store_dir))
        brief = second.briefing("proj")
        assert "2 tests pass via pytest -q" in brief
        assert "FastAPI + pytest." in brief


def test_absorbing_an_identical_run_twice_does_not_duplicate(tmp_path: Path) -> None:
        service = ProjectMemoryService(JsonMemoryStore(tmp_path))
        run = _result(
                final_output="one report",
                subagents=(SubagentResult.completed("explore", "one finding"),),
        )
        service.absorb("proj", run)
        memory = service.absorb("proj", run)
        assert len(memory.entries()) == 2  # report + finding, not four
