"""Delegation: the principal agent handing tasks to specialized subagents."""

from harness.delegation.delegate import (
        Delegate,
        SubagentRegistry,
        UnknownSubagentError,
)
from harness.delegation.report import SubagentReport

__all__ = [
        "Delegate",
        "SubagentRegistry",
        "SubagentReport",
        "UnknownSubagentError",
]
