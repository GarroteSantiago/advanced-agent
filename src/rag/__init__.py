"""RAG: chunking, embedding, vector storage, and retrieval over a corpus."""

from rag.chunk import Chunk, Chunker
from rag.ingest import gather_documents, ingest_corpus
from rag.retriever import Indexer, Retriever
from rag.store import NumpyVectorStore, Retrieved, VectorStore

__all__ = [
        "Chunk",
        "Chunker",
        "Indexer",
        "NumpyVectorStore",
        "Retrieved",
        "Retriever",
        "VectorStore",
        "gather_documents",
        "ingest_corpus",
]
