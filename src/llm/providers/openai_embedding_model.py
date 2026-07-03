"""An OpenAI-backed ``EmbeddingModel`` (outer-ring adapter).

Thin wrapper over the OpenAI embeddings endpoint; batch input in, list of
vectors out. Like ``OpenAIChatModel`` the network boundary is left untested --
the RAG core is tested with a fake embedder instead.
"""

from __future__ import annotations

from collections.abc import Sequence

from openai import AsyncOpenAI


class OpenAIEmbeddingModel:
        def __init__(self, *, model: str = "text-embedding-3-small", api_key: str | None = None) -> None:
                self._model = model
                self._client = AsyncOpenAI(api_key=api_key)

        def identifier(self) -> str:
                return self._model

        async def embed(self, texts: Sequence[str]) -> list[list[float]]:
                if not texts:
                        return []
                response = await self._client.embeddings.create(model=self._model, input=list(texts))
                return [list(item.embedding) for item in response.data]
