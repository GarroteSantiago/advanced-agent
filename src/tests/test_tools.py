"""Tests for the tools subsystem: registry, catalog, executor, and results."""

import pytest

from harness.events import AuditLogger, EventBus, ToolInvoked, ToolObserved
from harness.tools import (
        DuplicateToolError,
        ToolCatalog,
        ToolExecutor,
        ToolInterface,
        ToolRegistry,
        ToolRequest,
        ToolResult,
        UnknownToolError,
)
from harness.tools.adapters import EchoTool
from llm import Role, ToolCall


def test_echo_tool_conforms_to_port():
        tool: ToolInterface = EchoTool()
        assert isinstance(tool, ToolInterface)
        assert tool.name == "echo"


def test_tool_result_renders_itself_as_a_tool_message():
        ok = ToolResult.success(call_id="c1", tool_name="echo", content="hi")
        message = ok.to_message()
        assert message.role is Role.TOOL
        assert message.content == "hi"
        assert message.tool_call_id == "c1"
        assert message.name == "echo"


def test_failed_tool_result_message_uses_the_error_text():
        failed = ToolResult.failure(call_id="c1", tool_name="echo", error="boom")
        assert failed.to_message().content == "boom"


def test_registry_registers_and_looks_up_tools():
        registry = ToolRegistry()
        registry.register(EchoTool())
        assert registry.has("echo")
        assert registry.get("echo").name == "echo"
        assert len(registry) == 1


def test_registry_rejects_duplicate_names():
        registry = ToolRegistry()
        registry.register(EchoTool())
        with pytest.raises(DuplicateToolError):
                registry.register(EchoTool())


def test_registry_raises_on_unknown_tool():
        with pytest.raises(UnknownToolError):
                ToolRegistry().get("missing")


def test_catalog_renders_tool_schemas_for_the_model():
        registry = ToolRegistry()
        registry.register(EchoTool())
        catalog: ToolCatalog = registry.catalog()

        schemas = catalog.for_model()
        assert len(catalog) == 1
        assert schemas[0]["name"] == "echo"
        assert "parameters" in schemas[0]


def test_empty_catalog_reports_empty():
        assert ToolCatalog().is_empty()


async def test_executor_runs_tool_and_publishes_events():
        registry = ToolRegistry()
        registry.register(EchoTool())
        bus = EventBus()
        audit = AuditLogger()
        bus.subscribe(audit)
        executor = ToolExecutor(registry, bus)

        result = await executor.execute(
                ToolCall(id="c1", name="echo", arguments={"text": "hello"})
        )

        assert result.ok
        assert result.content == "hello"
        kinds = [type(e) for e in audit.records()]
        assert kinds == [ToolInvoked, ToolObserved]


async def test_executor_turns_unknown_tool_into_a_failed_result():
        executor = ToolExecutor(ToolRegistry())
        result = await executor.execute(ToolCall(id="c1", name="missing"))
        assert not result.ok
        assert "missing" in (result.error or "")


async def test_executor_converts_tool_exceptions_into_failed_results():
        class Exploding:
                @property
                def name(self) -> str:
                        return "boom"

                @property
                def description(self) -> str:
                        return "always raises"

                @property
                def mutates(self) -> bool:
                        return False

                def parameters(self) -> dict[str, object]:
                        return {}

                async def invoke(self, request: ToolRequest) -> ToolResult:
                        raise RuntimeError("kaboom")

        registry = ToolRegistry()
        registry.register(Exploding())
        executor = ToolExecutor(registry)

        result = await executor.execute(ToolCall(id="c1", name="boom"))
        assert not result.ok
        assert "kaboom" in (result.error or "")
