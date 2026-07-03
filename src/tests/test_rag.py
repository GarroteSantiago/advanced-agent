"""Tests for the RAG core: chunking, store, retrieval, and persistence."""

from __future__ import annotations

from collections.abc import Sequence

from rag import Chunker, Indexer, NumpyVectorStore, Retriever, gather_documents

# A tiny fixed vocabulary lets a fake embedder produce deterministic vectors so
# similarity is meaningful without a real model.
_VOCAB = ("routing", "auth", "testing", "widget")


class FakeEmbeddingModel:
        def identifier(self) -> str:
                return "fake-embed"

        async def embed(self, texts: Sequence[str]) -> list[list[float]]:
                return [[float(text.lower().count(term)) for term in _VOCAB] for text in texts]


def test_chunker_splits_with_overlap() -> None:
        chunker = Chunker(size=10, overlap=4)
        chunks = chunker.chunk("abcdefghijklmnopqr", source="doc")

        assert [c.ordinal for c in chunks] == list(range(len(chunks)))
        assert all(c.source == "doc" for c in chunks)
        assert chunks[0].text == "abcdefghij"
        # step = size - overlap = 6, so the second window starts at index 6.
        assert chunks[1].text.startswith("g")


def test_chunker_ignores_blank_text() -> None:
        assert Chunker().chunk("   \n  ", source="doc") == []


async def test_retriever_returns_the_most_relevant_chunk() -> None:
        store = NumpyVectorStore()
        indexer = Indexer(FakeEmbeddingModel(), store, Chunker(size=200, overlap=0))
        await indexer.index(
                [
                        ("routing.md", "routing routing APIRouter path operations"),
                        ("auth.md", "auth auth security oauth tokens"),
                ]
        )

        retriever = Retriever(FakeEmbeddingModel(), store)
        results = await retriever.retrieve("how does routing work", k=1)

        assert len(results) == 1
        assert results[0].chunk.source == "routing.md"
        assert results[0].score > 0


async def test_store_persists_and_reloads(tmp_path) -> None:
        store = NumpyVectorStore()
        await Indexer(FakeEmbeddingModel(), store, Chunker(size=200, overlap=0)).index(
                [("widget.md", "widget widget testing widget")]
        )
        store.save(tmp_path / "index")

        reloaded = NumpyVectorStore.load(tmp_path / "index")
        assert len(reloaded) == len(store)

        results = Retriever(FakeEmbeddingModel(), reloaded)
        found = await results.retrieve("widget", k=1)
        assert found[0].chunk.source == "widget.md"


def test_gather_documents_reads_supported_files(tmp_path) -> None:
        (tmp_path / "a.md").write_text("alpha", encoding="utf-8")
        (tmp_path / "nested").mkdir()
        (tmp_path / "nested" / "b.txt").write_text("beta", encoding="utf-8")
        (tmp_path / "ignore.png").write_bytes(b"\x89PNG")

        docs = dict(gather_documents(tmp_path))

        assert docs == {"a.md": "alpha", "nested/b.txt": "beta"}
