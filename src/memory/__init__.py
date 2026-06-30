"""Memory layer (deferred seam).

Project-persistent memory beyond a single conversation: ``ConversationMemory``
(session history/summaries) and ``VectorMemory`` (embeddings + vector store for
RAG over technical docs). ``VectorMemory`` is what will pull ``EmbeddingModel``
into ``llm`` when it lands.

Deferred to a later increment; nothing here yet.
"""
