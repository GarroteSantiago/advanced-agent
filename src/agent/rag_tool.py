"""The Researcher's RAG tool and its retrieval log.

``RagSearchTool`` retrieves from the framework corpus and returns the matching
fragments (so the model -- and the trace -- see *which* fragments were used). It
also (a) publishes a ``DocumentsRetrieved`` event for observability and (b)
records each hit's ``Source`` (tagged ``Origin.RAG``) into a ``RetrievalLog`` the
subagent drains into its report, so retrieved provenance reaches the shared
ledger. This lives in the agent layer because it bridges ``rag`` and ``harness``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from harness.events import DocumentsRetrieved, EventBus
from harness.runtime import Source
from harness.tools import ToolRequest, ToolResult
from rag import Retrieved, Retriever


class RetrievalLog:
        """Collects the sources retrieved during one subagent run."""

        def __init__(self) -> None:
                self._sources: list[Source] = []

        def record(self, source: Source) -> None:
                self._sources.append(source)

        def drain(self) -> tuple[Source, ...]:
                collected = tuple(self._sources)
                self._sources.clear()
                return collected


class RagSearchTool:
        """Searches the indexed framework documentation."""

        def __init__(
                self,
                retriever: Retriever,
                log: RetrievalLog | None = None,
                event_bus: EventBus | None = None,
                k: int = 4,
        ) -> None:
                self._retriever = retriever
                self._log = log
                self._bus = event_bus
                self._k = k

        @property
        def name(self) -> str:
                return "rag_search"

        @property
        def description(self) -> str:
                return (
                        "Search the indexed framework documentation for relevant passages. "
                        "Use this BEFORE web search; fall back to the web only if this is thin."
                )

        @property
        def mutates(self) -> bool:
                return False

        def parameters(self) -> Mapping[str, object]:
                return {
                        "type": "object",
                        "properties": {"query": {"type": "string", "description": "What to look up."}},
                        "required": ["query"],
                }

        async def invoke(self, request: ToolRequest) -> ToolResult:
                query = str(request.arguments.get("query", ""))
                hits = await self._retriever.retrieve(query, self._k)

                for hit in hits:
                        if self._log is not None:
                                self._log.record(Source.from_rag(hit.chunk.source))
                if self._bus is not None:
                        self._bus.publish(
                                DocumentsRetrieved(
                                        query=query,
                                        sources=tuple(hit.chunk.source for hit in hits),
                                )
                        )

                return ToolResult.success(
                        call_id=request.call_id, tool_name=self.name, content=_format(hits)
                )


def _format(hits: Sequence[Retrieved]) -> str:
        if not hits:
                return "no relevant documentation found"
        return "\n\n".join(
                f"[{hit.chunk.source}] (score {hit.score:.2f})\n{hit.chunk.text}" for hit in hits
        )
