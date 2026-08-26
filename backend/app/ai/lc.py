"""LangChain 集成：ChatOpenAI 与 OpenAIEmbeddings（可插拔，离线回退由调用方处理）。

统一走 OpenAI 兼容接口，可接 OpenAI / 通义 / 智谱 / DeepSeek / 本地 vLLM 等。
未配置 key 时 get_* 返回 None，调用方回退到离线方案。
"""
from __future__ import annotations

import os
from functools import lru_cache

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from ..config import settings

# 禁用代理以避免SOCKS代理问题
os.environ["NO_PROXY"] = "*"
os.environ["http_proxy"] = ""
os.environ["https_proxy"] = ""
os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""
os.environ["ALL_PROXY"] = ""
os.environ["all_proxy"] = ""


@lru_cache(maxsize=1)
def get_chat_model() -> ChatOpenAI | None:
    if not settings.llm_enabled:
        return None
    return ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        temperature=0.7,
        max_tokens=400,
        timeout=30.0,
        http_client_kwargs={"trust_env": False},  # 禁用环境变量代理
    )


@lru_cache(maxsize=1)
def get_embeddings_model() -> OpenAIEmbeddings | None:
    if not settings.embedding_enabled:
        return None
    return OpenAIEmbeddings(
        model=settings.embedding_model,
        api_key=settings.embedding_api_key,
        base_url=settings.embedding_base_url,
        timeout=30.0,
        http_client_kwargs={"trust_env": False},  # 禁用环境变量代理
    )


def llm_generate(system: str, human: str, max_tokens: int = 400) -> str | None:
    """用 LangChain ChatOpenAI 生成文本；失败/未配置返回 None。"""
    model = get_chat_model()
    if model is None:
        return None
    try:
        resp = model.invoke(
            [SystemMessage(content=system), HumanMessage(content=human)],
            max_tokens=max_tokens,
        )
        content = resp.content if isinstance(resp.content, str) else str(resp.content)
        return content.strip() or None
    except Exception:  # noqa: BLE001
        return None


def embed_documents(texts: list[str]) -> list[list[float]] | None:
    """用 LangChain OpenAIEmbeddings 批量嵌入；失败/未配置返回 None。"""
    model = get_embeddings_model()
    if model is None:
        return None
    try:
        return model.embed_documents(texts)
    except Exception:  # noqa: BLE001
        return None
