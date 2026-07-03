"""Tests for the delegation core: report, registry, and catalog rendering."""

from __future__ import annotations

from collections.abc import Mapping

import pytest

from harness.delegation import (
        Delegate,
        SubagentRegistry,
        SubagentReport,
        UnknownSubagentError,
)
from harness.runtime import Source
from harness.tools import ToolCatalog


class FakeDelegate:
        """A scripted ``Delegate`` for tests."""

        def __init__(self, name: str, report: SubagentReport) -> None:
                self._name = name
                self._report = report

        @property
        def name(self) -> str:
                return self._name

        @property
        def description(self) -> str:
                return f"the {self._name} subagent"

        def parameters(self) -> Mapping[str, object]:
                return {
                        "type": "object",
                        "properties": {"task": {"type": "string"}},
                        "required": ["task"],
                }

        async def delegate(self, task: str) -> SubagentReport:
                return self._report


def test_registry_resolves_known_and_rejects_unknown() -> None:
        explorer = FakeDelegate("explore", SubagentReport.completed("explore", "mapped"))
        registry = SubagentRegistry([explorer])

        assert registry.knows("explore")
        assert registry.resolve("explore") is explorer
        assert not registry.knows("ghost")
        with pytest.raises(UnknownSubagentError):
                registry.resolve("ghost")


def test_delegate_conforms_to_the_port_structurally() -> None:
        delegate: Delegate = FakeDelegate("test", SubagentReport.completed("test", "green"))
        assert isinstance(delegate, Delegate)


def test_catalog_renders_a_subagent_like_a_tool() -> None:
        explorer = FakeDelegate("explore", SubagentReport.completed("explore", "mapped"))
        catalog = ToolCatalog.of_tools([explorer])

        schema = catalog.for_model()[0]
        assert schema["name"] == "explore"
        assert schema["description"] == "the explore subagent"


def test_report_carries_provenance_for_the_ledger() -> None:
        report = SubagentReport(
                agent="research",
                output="found the router docs",
                sources=(Source.from_rag("fastapi/routing"),),
                observations=("uses APIRouter",),
        )

        assert report.succeeded is True
        assert report.sources[0].reference == "fastapi/routing"
        assert report.observations == ("uses APIRouter",)
