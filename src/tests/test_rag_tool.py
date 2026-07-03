"""Tests for the RAG tool and its wiring into a subagent's report."""

from __future__ import annotations

from agent.rag_tool import RagSearchTool, RetrievalLog
from agent.subagent import Subagent
from harness.events import AuditLogger, DocumentsRetrieved, EventBus
from harness.runtime import Origin
from harness.tools import ToolRequest
from llm import Completion, ToolCall
from rag import Chunker, Indexer, NumpyVectorStore, Retriever
from tests.doubles import FakeChatModel
from tests.test_rag import FakeEmbeddingModel


async def _routing_retriever() -> Retriever:
        store = NumpyVectorStore()
        await Indexer(FakeEmbeddingModel(), store, Chunker(size=200, overlap=0)).index(
                [("routing.md", "routing routing APIRouter path operations")]
        )
        return Retriever(FakeEmbeddingModel(), store)


async def test_rag_search_returns_fragments_records_sources_and_emits_event() -> None:
        log = RetrievalLog()
        bus = EventBus()
        audit = AuditLogger()
        bus.subscribe(audit)
        tool = RagSearchTool(await _routing_retriever(), log, bus, k=1)

        result = await tool.invoke(
                ToolRequest(call_id="c1", tool_name="rag_search", arguments={"query": "routing"})
        )

        assert result.ok
        assert "routing.md" in result.content
        recorded = log.drain()
        assert len(recorded) == 1
        assert recorded[0].origin is Origin.RAG
        assert recorded[0].reference == "routing.md"
        events = [e for e in audit.records() if isinstance(e, DocumentsRetrieved)]
        assert len(events) == 1
        assert events[0].sources == ("routing.md",)


async def test_subagent_surfaces_retrieved_sources_in_its_report() -> None:
        log = RetrievalLog()
        tool = RagSearchTool(await _routing_retriever(), log, k=1)
        model = FakeChatModel(
                [
                        Completion(
                                tool_calls=(
                                        ToolCall(id="c1", name="rag_search", arguments={"query": "routing"}),
                                )
                        ),
                        Completion(content="APIRouter handles routing."),
                ]
        )
        researcher = Subagent(
                name="research",
                description="looks things up",
                system_prompt="You are the Researcher.",
                model=model,
                tools=[tool],
                retrieval_log=log,
        )

        report = await researcher.delegate("how does routing work")

        assert report.succeeded is True
        assert [s.reference for s in report.sources] == ["routing.md"]
        assert report.sources[0].origin is Origin.RAG
