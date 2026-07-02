"""Tests for the basic-TP tool adapters (offline, deterministic)."""

from harness.tools import ToolInterface, ToolRequest
from harness.tools.adapters import (
        ListFilesTool,
        ReadFileTool,
        RunCommandTool,
        WebSearchTool,
        WriteFileTool,
)


def _request(name: str, **arguments: object) -> ToolRequest:
        return ToolRequest(call_id="c1", tool_name=name, arguments=arguments)


def test_all_tools_conform_to_the_port():
        for tool in (
                ReadFileTool(),
                WriteFileTool(),
                RunCommandTool(),
                ListFilesTool(),
                WebSearchTool(),
        ):
                assert isinstance(tool, ToolInterface)


def test_mutation_classification_matches_the_spec():
        read_only = {ReadFileTool().name, ListFilesTool().name, WebSearchTool().name}
        mutating = {WriteFileTool().name, RunCommandTool().name}

        assert not any(tool.mutates for tool in (ReadFileTool(), ListFilesTool(), WebSearchTool()))
        assert all(tool.mutates for tool in (WriteFileTool(), RunCommandTool()))
        assert read_only == {"read_file", "list_files", "web_search"}
        assert mutating == {"write_file", "run_command"}


async def test_read_file_returns_contents(tmp_path):
        target = tmp_path / "hello.txt"
        target.write_text("contents here", encoding="utf-8")

        result = await ReadFileTool().invoke(_request("read_file", path=str(target)))
        assert result.ok
        assert result.content == "contents here"


async def test_read_file_reports_missing_file():
        result = await ReadFileTool().invoke(_request("read_file", path="/no/such/file"))
        assert not result.ok


async def test_write_file_replaces_content(tmp_path):
        target = tmp_path / "out.txt"

        result = await WriteFileTool().invoke(
                _request("write_file", path=str(target), content="new body")
        )
        assert result.ok
        assert target.read_text(encoding="utf-8") == "new body"


async def test_write_file_reports_the_path_it_modified(tmp_path):
        target = tmp_path / "out.txt"
        result = await WriteFileTool().invoke(
                _request("write_file", path=str(target), content="body")
        )
        assert result.modified == (str(target),)


async def test_a_failed_write_reports_no_modified_files():
        result = await WriteFileTool().invoke(_request("write_file", path="/no/such/dir/x"))
        assert not result.ok
        assert result.modified == ()


async def test_list_files_lists_directory_entries(tmp_path):
        (tmp_path / "a.txt").write_text("", encoding="utf-8")
        (tmp_path / "sub").mkdir()

        result = await ListFilesTool().invoke(_request("list_files", path=str(tmp_path)))
        assert result.ok
        assert "a.txt" in result.content
        assert "sub/" in result.content


async def test_run_command_captures_output():
        result = await RunCommandTool().invoke(_request("run_command", command="echo hello-loop"))
        assert result.ok
        assert "hello-loop" in result.content
        assert "exit_code=0" in result.content


async def test_web_search_without_key_fails_clearly(monkeypatch):
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        result = await WebSearchTool().invoke(_request("web_search", query="anything"))
        assert not result.ok
        assert "TAVILY_API_KEY" in (result.error or "")
