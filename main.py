"""Entry point: launch the interactive coding-agent chat.

Wires the console I/O adapters, the LLM provider (OpenAI when OPENAI_API_KEY is
set, else a placeholder), and the optional guardrails config, then runs the chat.
"""

import asyncio
import os
from pathlib import Path

from agent import Session
from agent.cli import build_session, run_chat
from agent.interaction import ConsoleInputer, ConsoleRenderer, Renderer
from harness.tools import PolicyConfig
from llm import ChatModel
from llm.providers import OpenAIChatModel, OpenAIEmbeddingModel, PlaceholderChatModel
from rag import NumpyVectorStore, Retriever


def _load_dotenv(path: str = ".env") -> None:
        file = Path(path)
        if not file.exists():
                return
        for raw in file.read_text(encoding="utf-8").splitlines():
                entry = raw.strip()
                if not entry or entry.startswith("#") or "=" not in entry:
                        continue
                key, _, value = entry.partition("=")
                os.environ.setdefault(key.strip(), value.strip())


def _load_policy(path: str = "agent.config.toml") -> PolicyConfig | None:
        file = Path(path)
        return PolicyConfig.from_toml(file) if file.exists() else None


def _enable_observability(session: Session, renderer: Renderer) -> None:
        """Subscribe the Phoenix tracer when OBSERVABILITY=phoenix.

        Opt-in and best-effort: if the extra is not installed we warn and carry
        on rather than crashing the CLI.
        """
        if os.environ.get("OBSERVABILITY") != "phoenix":
                return
        try:
                from observability.phoenix import launch_phoenix_tracer
        except ImportError:
                renderer.show(
                        "OBSERVABILITY=phoenix set, but the extra is missing; "
                        "run `uv sync --extra observability`."
                )
                return
        tracer = launch_phoenix_tracer()
        session.events.subscribe(tracer)
        renderer.show("observability: Phoenix tracing enabled (local UI launched)")


def _build_retriever(renderer: Renderer) -> Retriever | None:
        """Load the RAG index when it exists and a key is available, else None.

        Without a retriever the Researcher falls back to web search only.
        """
        index_dir = Path(os.environ.get("RAG_INDEX_DIR", "data/rag_index"))
        if not os.environ.get("OPENAI_API_KEY") or not (index_dir / "chunks.json").exists():
                return None
        embedder = OpenAIEmbeddingModel(
                model=os.environ.get("EMBED_MODEL", "text-embedding-3-small")
        )
        renderer.show(f"RAG: loaded index from {index_dir}")
        return Retriever(embedder, NumpyVectorStore.load(index_dir))


def _build_model(renderer: Renderer) -> ChatModel:
        if os.environ.get("OPENAI_API_KEY"):
                model_name = os.environ.get("MODEL", "gpt-5-nano")
                renderer.show(f"using OpenAI model: {model_name}")
                return OpenAIChatModel(model=model_name)
        renderer.show(
                "WARNING: no OPENAI_API_KEY set; using a placeholder model. "
                "Set it in .env for real tasks."
        )
        return PlaceholderChatModel()


async def _main() -> None:
        _load_dotenv()
        renderer = ConsoleRenderer()
        inputer = ConsoleInputer()

        policy = _load_policy()
        if policy is not None:
                renderer.show("loaded guardrails from agent.config.toml")

        model = _build_model(renderer)
        retriever = _build_retriever(renderer)
        session, supervision, plan_mode, progress = build_session(
                model, renderer=renderer, inputer=inputer, policy=policy, retriever=retriever
        )
        _enable_observability(session, renderer)
        await run_chat(
                session,
                supervision=supervision,
                plan_mode=plan_mode,
                progress=progress,
                renderer=renderer,
                inputer=inputer,
        )


def main() -> None:
        asyncio.run(_main())


if __name__ == "__main__":
        main()
