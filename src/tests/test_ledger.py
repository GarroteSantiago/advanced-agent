"""Tests for the shared task ledger value objects."""

from __future__ import annotations

from harness.runtime.ledger import Origin, Source, SubagentResult, TaskLedger


def test_for_request_seeds_request_and_empty_collections() -> None:
        ledger = TaskLedger.for_request("analyze the repo")

        assert ledger.original_request() == "analyze the repo"
        assert ledger.progress() == ()
        assert ledger.subagent_results() == ()
        assert ledger.sources_consulted() == ()
        assert ledger.modified_files() == ()
        assert ledger.observations() == ()


def test_transitions_are_copy_on_write() -> None:
        base = TaskLedger.for_request("task")

        grown = base.with_observation("found a router").with_progress("explored src/")

        assert base.observations() == ()
        assert base.progress() == ()
        assert grown.observations() == ("found a router",)
        assert grown.progress() == ("explored src/",)


def test_records_accumulate_in_order() -> None:
        ledger = (
                TaskLedger.for_request("task")
                .with_observation("first")
                .with_observation("second")
        )

        assert ledger.observations() == ("first", "second")


def test_modified_files_dedup_preserving_first_seen_order() -> None:
        ledger = (
                TaskLedger.for_request("task")
                .with_modified_file("a.py")
                .with_modified_file("b.py")
                .with_modified_file("a.py")
        )

        assert ledger.modified_files() == ("a.py", "b.py")


def test_source_factories_tag_origin() -> None:
        assert Source.from_repo("src/app.py").origin is Origin.REPO
        assert Source.from_memory("architecture").origin is Origin.MEMORY
        assert Source.from_rag("fastapi/routing").origin is Origin.RAG
        assert Source.from_web("https://fastapi.tiangolo.com").origin is Origin.WEB
        assert Source.inferred("guessed from naming").origin is Origin.INFERENCE


def test_sources_retain_origin_differentiation() -> None:
        ledger = (
                TaskLedger.for_request("task")
                .with_source(Source.from_repo("src/app.py"))
                .with_source(Source.from_rag("fastapi/routing"))
        )

        origins = tuple(source.origin for source in ledger.sources_consulted())
        assert origins == (Origin.REPO, Origin.RAG)


def test_subagent_result_factories_set_success() -> None:
        assert SubagentResult.completed("Explorer", "mapped the tree").succeeded is True
        assert SubagentResult.failed("Tester", "build broke").succeeded is False


def test_subagent_results_accumulate() -> None:
        ledger = (
                TaskLedger.for_request("task")
                .with_subagent_result(SubagentResult.completed("Explorer", "done"))
                .with_subagent_result(SubagentResult.failed("Tester", "red"))
        )

        agents = tuple(result.agent for result in ledger.subagent_results())
        assert agents == ("Explorer", "Tester")
