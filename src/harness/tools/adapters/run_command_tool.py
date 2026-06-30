"""run_command: run a shell command and return its output (mutating)."""

from __future__ import annotations

import subprocess
from collections.abc import Mapping

from harness.tools.request import ToolRequest
from harness.tools.result import ToolResult


class RunCommandTool:
        """Runs a terminal command, capturing stdout and stderr.

        A non-zero exit code is a successful *observation* (the command ran; its
        output is returned), not a tool failure. Only infrastructure faults
        (timeout) are reported as failures.
        """

        def __init__(self, timeout_seconds: int = 120) -> None:
                self._timeout = timeout_seconds

        @property
        def name(self) -> str:
                return "run_command"

        @property
        def description(self) -> str:
                return "Run a shell command and return its combined stdout and stderr."

        @property
        def mutates(self) -> bool:
                return True

        def parameters(self) -> Mapping[str, object]:
                return {
                        "type": "object",
                        "properties": {"command": {"type": "string"}},
                        "required": ["command"],
                }

        async def invoke(self, request: ToolRequest) -> ToolResult:
                command = request.arguments.get("command")
                if not isinstance(command, str):
                        return ToolResult.failure(
                                call_id=request.call_id,
                                tool_name=self.name,
                                error="run_command requires a string 'command' argument",
                        )
                try:
                        completed = subprocess.run(
                                command,
                                shell=True,
                                capture_output=True,
                                text=True,
                                timeout=self._timeout,
                        )
                except subprocess.TimeoutExpired:
                        return ToolResult.failure(
                                call_id=request.call_id,
                                tool_name=self.name,
                                error=f"command timed out after {self._timeout}s",
                        )
                output = completed.stdout + completed.stderr
                return ToolResult.success(
                        call_id=request.call_id,
                        tool_name=self.name,
                        content=f"exit_code={completed.returncode}\n{output}",
                )
