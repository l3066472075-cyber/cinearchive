"""LLM / 嵌入接入层：直接调用 OpenAI 兼容接口（httpx，稳定可靠）。

说明：早期用 langchain-openai 的 ChatOpenAI/OpenAIEmbeddings，但该版本存在
「http_client_kwargs 被错误传入 model_kwargs」的 bug，导致部分调用静默失败。
改为 httpx 直连后彻底规避；LangGraph 推荐图（langgraph）仍为编排核心。
"""
from __future__ import annotations

import httpx

from ..config import settings

_client = httpx.Client(timeout=90.0)


def llm_generate(system: str, human: str, max_tokens: int = 400) -> str | None:
    """调用 OpenAI 兼容 chat/completions。失败返回 None（调用方回退模板）。"""
    if not settings.llm_enabled:
        return None
    try:
        resp = _client.post(
            f"{settings.llm_base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {settings.llm_api_key}"},
            json={
                "model": settings.llm_model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": human},
                ],
                "max_tokens": max_tokens,
                "temperature": 0.7,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception:  # noqa: BLE001
        return None


def embed_documents(texts: list[str]) -> list[list[float]] | None:
    """调用 OpenAI 兼容 embeddings 接口。失败返回 None（调用方回退哈希）。"""
    if not settings.embedding_enabled:
        return None
    try:
        resp = _client.post(
            f"{settings.embedding_base_url.rstrip('/')}/embeddings",
            headers={"Authorization": f"Bearer {settings.embedding_api_key}"},
            json={"model": settings.embedding_model, "input": texts},
        )
        resp.raise_for_status()
        data = resp.json()
        return [item["embedding"] for item in data["data"]]
    except Exception:  # noqa: BLE001
        return None
