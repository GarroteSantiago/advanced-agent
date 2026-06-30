"""web_search: search the web via Tavily (read-only).

Degrades gracefully: with no ``TAVILY_API_KEY`` it returns a clear error rather
than raising, so the rest of the agent keeps working.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import Mapping

from tavily import TavilyClient

from harness.tools.request import ToolRequest
from harness.tools.result import ToolResult


class WebSearchTool:
        @property
        def name(self) -> str:
                return "web_search"

        @property
        def description(self) -> str:
                return "Search the web for information and return the top results."

        @property
        def mutates(self) -> bool:
                return False

        def parameters(self) -> Mapping[str, object]:
                return {
                        "type": "object",
                        "properties": {"query": {"type": "string"}},
                        "required": ["query"],
                }

        async def invoke(self, request: ToolRequest) -> ToolResult:
                query = request.arguments.get("query")
                if not isinstance(query, str):
                        return ToolResult.failure(
                                call_id=request.call_id,
                                tool_name=self.name,
                                error="web_search requires a string 'query' argument",
                        )
                api_key = os.environ.get("TAVILY_API_KEY")
                if not api_key:
                        return ToolResult.failure(
                                call_id=request.call_id,
                                tool_name=self.name,
                                error="web_search needs TAVILY_API_KEY to be set",
                        )
                try:
                        client = TavilyClient(api_key=api_key)
                        response = await asyncio.to_thread(client.search, query)
                except Exception as error:
                        return ToolResult.failure(
                                call_id=request.call_id,
                                tool_name=self.name,
                                error=f"{type(error).__name__}: {error}",
                        )
                return ToolResult.success(
                        call_id=request.call_id,
                        tool_name=self.name,
                        content=self._format(response),
                )

        @staticmethod
        def _format(response: object) -> str:
                results = response.get("results", []) if isinstance(response, dict) else []
                lines = [
                        f"- {item.get('title', '')}: {item.get('url', '')}\n  {item.get('content', '')}"
                        for item in results
                        if isinstance(item, dict)
                ]
                return "\n".join(lines) or "no results"
