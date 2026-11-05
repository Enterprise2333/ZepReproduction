"""Shared Graphiti/DeepSeek runtime for the reproduction."""

import asyncio
import os
import time
from pathlib import Path

os.environ["EMBEDDING_DIM"] = "384"
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
os.environ["GRAPHITI_TELEMETRY_ENABLED"] = "false"

from dotenv import load_dotenv
from fastembed import TextEmbedding
from graphiti_core import Graphiti
from graphiti_core.cross_encoder.client import CrossEncoderClient
from graphiti_core.driver.kuzu_driver import KuzuDriver
from graphiti_core.embedder.client import EmbedderClient
from graphiti_core.llm_client.config import LLMConfig
from graphiti_core.llm_client.openai_generic_client import OpenAIGenericClient
from openai import AsyncOpenAI

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")
MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")


class LocalEmbedder(EmbedderClient):
    def __init__(self):
        self.model = TextEmbedding(
            model_name="BAAI/bge-small-en-v1.5",
            cache_dir=str(ROOT / "model_cache"),
            local_files_only=True,
        )

    async def create(self, input_data):
        return (await self.create_batch([str(input_data)]))[0]

    async def create_batch(self, input_data_list):
        if not input_data_list:
            return []
        return await asyncio.to_thread(
            lambda: [x.tolist() for x in self.model.embed(input_data_list)]
        )


class LexicalReranker(CrossEncoderClient):
    async def rank(self, query, passages):
        terms = set(query.lower().split())
        return sorted(
            ((p, float(len(terms & set(p.lower().split())))) for p in passages),
            key=lambda x: x[1],
            reverse=True,
        )


class TrackedLLM(OpenAIGenericClient):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.calls = 0
        self.seconds = 0.0
        self.estimated_input_chars = 0
        self.estimated_output_chars = 0

    async def _generate_response(self, messages, *args, **kwargs):
        self.calls += 1
        self.estimated_input_chars += sum(len(m.content) for m in messages)
        start = time.perf_counter()
        try:
            result = await super()._generate_response(messages, *args, **kwargs)
            self.estimated_output_chars += len(str(result))
            return result
        finally:
            self.seconds += time.perf_counter() - start


def require_key():
    key = os.getenv("DEEPSEEK_API_KEY")
    if not key:
        raise RuntimeError("Set DEEPSEEK_API_KEY in .env")
    return key


def make_graph(db_path: Path) -> tuple[Graphiti, TrackedLLM]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    llm = TrackedLLM(
        config=LLMConfig(
            api_key=require_key(),
            base_url="https://api.deepseek.com/v1",
            model=MODEL,
            small_model=MODEL,
            temperature=0,
        ),
        structured_output_mode="json_object",
        max_tokens=4096,
    )
    graph = Graphiti(
        graph_driver=KuzuDriver(db=str(db_path)),
        llm_client=llm,
        embedder=LocalEmbedder(),
        cross_encoder=LexicalReranker(),
        max_coroutines=2,
    )
    return graph, llm


async def prepare_graph(graph: Graphiti):
    # graph.build_indices_and_constraints() is a no-op for Kuzu in upstream 0.31.2.
    await graph.driver.graph_ops.build_indices_and_constraints(graph.driver)


def answer_client():
    return AsyncOpenAI(api_key=require_key(), base_url="https://api.deepseek.com/v1")

