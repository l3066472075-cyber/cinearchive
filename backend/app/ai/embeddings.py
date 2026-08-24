"""文本嵌入层：可插拔。

- 若配置了 EMBEDDING_BASE_URL + EMBEDDING_API_KEY，走 OpenAI 兼容的嵌入接口
  （可接 text-embedding-3 / bge / qwen / 智谱 embedding 等）。
- 否则回退到「字符 n-gram 特征哈希」：中文按字符 bigram/trigram，英文按词 +
  字符 n-gram，用 signed hashing 投影到固定维度。零依赖、离线可跑，能提供
  不错的"浅层语义"相似度，足以支撑 MVP 演示；接真实嵌入后直接替换即可。
"""
from __future__ import annotations

import hashlib
import math
import re
from functools import lru_cache

import httpx

from ..config import settings

_DIM = settings.hash_embedding_dim

# 停用词（中英文常见虚词，降低噪音）
_STOPWORDS = {
    "的", "了", "我", "你", "他", "她", "它", "是", "在", "和", "与", "很", "不",
    "都", "也", "就", "有", "而", "及", "或", "又", "啊", "吧", "呢", "吗", "这",
    "那", "个", "们", "着", "过", "把", "被", "让", "给", "对", "从", "到",
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "is", "are", "was",
    "were", "be", "been", "it", "this", "that", "with", "for", "as", "by", "at",
    "about", "into", "through", "i", "my", "me", "we", "our", "you", "your",
}


def _tokenize(text: str) -> list[str]:
    """混合切分：中文按字切出 bigram/trigram，英文按单词 + 字符 n-gram。"""
    text = (text or "").lower().strip()
    if not text:
        return []
    # 分离中文字符序列与英文/数字序列
    tokens: list[str] = []
    # 英文单词
    words = re.findall(r"[a-z0-9]+", text)
    for w in words:
        if w not in _STOPWORDS and len(w) > 1:
            tokens.append(w)
        # 字符 bigram 兜底
        tokens.extend(w[i : i + 2] for i in range(len(w) - 1))
    # 中文字符 n-gram
    cjk = re.findall(r"[\u4e00-\u9fff]+", text)
    for seg in cjk:
        chars = [c for c in seg if c not in _STOPWORDS]
        tokens.extend(chars)  # unigram 保留单字（中文单字本身有义）
        tokens.extend("".join(chars[i : i + 2]) for i in range(len(chars) - 1))
        tokens.extend("".join(chars[i : i + 3]) for i in range(len(chars) - 2))
    return tokens


def _signed_hash(token: str, dim: int = _DIM) -> tuple[int, int]:
    """返回 (bucket_index, sign)，用于 signed feature hashing。"""
    h = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
    return h % dim, 1 if (h >> 63) & 1 else -1


def hash_embed(text: str, dim: int = _DIM) -> list[float]:
    """离线特征哈希嵌入。"""
    vec = [0.0] * dim
    tokens = _tokenize(text)
    if not tokens:
        return vec
    for tok in tokens:
        idx, sign = _signed_hash(tok, dim)
        vec[idx] += sign
    # L2 归一化
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def cosine(a: list[float], b: list[float]) -> float:
    """余弦相似度（输入已归一化时即点积）。"""
    if not a or not b or len(a) != len(b):
        return 0.0
    return sum(x * y for x, y in zip(a, b))


def embed_remote(texts: list[str]) -> list[list[float]]:
    """调用 LangChain OpenAIEmbeddings（OpenAI 兼容嵌入接口）。失败时抛异常，由调用方回退。"""
    from . import lc  # 局部导入避免循环依赖

    vecs = lc.embed_documents(texts)
    if vecs is None:
        raise RuntimeError("embedding 服务不可用")
    return vecs


@lru_cache(maxsize=2048)
def embed_text_cached(text: str) -> tuple[float, ...]:
    """对单条文本的嵌入（带缓存）。无 key 时用离线哈希。"""
    if settings.embedding_enabled:
        try:
            return tuple(embed_remote([text])[0])
        except Exception:  # noqa: BLE001 - 网络/鉴权失败时静默回退
            pass
    return tuple(hash_embed(text))


def embed_text(text: str) -> list[float]:
    return list(embed_text_cached(text))
