"""应用配置。

所有可配置项都通过环境变量 / .env 覆盖，保证零配置即可运行。
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# 项目根（backend 目录）与仓库根
BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BACKEND_DIR.parent

# 允许用户在工作目录或 backend 目录放置 .env
load_dotenv(REPO_DIR / ".env")
load_dotenv(BACKEND_DIR / ".env")


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


class Settings:
    app_name: str = "CineArchive · 影视教育资源库"
    version: str = "0.1.0"

    # 数据库文件路径（默认放在 backend/data/ 下）
    database_url: str = _env(
        "CINELIB_DATABASE_URL",
        f"sqlite:///{BACKEND_DIR / 'data' / 'cinelib.db'}",
    )

    # —— 可插拔 AI 层 ——
    # 只要设置 LLM_API_KEY + LLM_BASE_URL，就会走真实大模型；否则使用离线回退。
    llm_api_key: str = _env("LLM_API_KEY")
    llm_base_url: str = _env("LLM_BASE_URL")
    llm_model: str = _env("LLM_MODEL", "gpt-4o-mini")
    # 嵌入模型走 OpenAI 兼容接口（可接 bge / qwen / openai 等）
    embedding_base_url: str = _env("EMBEDDING_BASE_URL", llm_base_url)
    embedding_api_key: str = _env("EMBEDDING_API_KEY", llm_api_key)
    embedding_model: str = _env("EMBEDDING_MODEL", "text-embedding-3-small")

    # 离线 n-gram 哈希嵌入的维度（无 API key 时的回退方案）
    hash_embedding_dim: int = 512

    # —— 微信静默登录（小程序 code2session + 公众号 H5 OAuth 共用）——
    # 提供 AppID / AppSecret 后即可真实调用；留空则进入开发模式 mock。
    wx_appid: str = _env("WX_APPID")
    wx_app_secret: str = _env("WX_APP_SECRET")
    # 公众号 H5 网页授权的回调地址（需在公众号「网页授权域名」下）；
    # 留空则按请求的 Host 自动拼接 /api/v1/auth/mp/callback。
    mp_oauth_redirect_uri: str = _env("MP_OAUTH_REDIRECT_URI")

    # —— JWT 鉴权 ——
    jwt_secret: str = _env("JWT_SECRET", "cinelib-dev-secret-change-me")
    jwt_algorithm: str = _env("JWT_ALGORITHM", "HS256")
    jwt_expire_minutes: int = int(_env("JWT_EXPIRE_MINUTES", "10080") or 10080)  # 默认 7 天

    @property
    def llm_enabled(self) -> bool:
        return bool(self.llm_api_key and self.llm_base_url)

    @property
    def embedding_enabled(self) -> bool:
        return bool(self.embedding_api_key and self.embedding_base_url)

    @property
    def wx_enabled(self) -> bool:
        """是否已配置微信 AppID/AppSecret（决定登录走真实接口还是开发模式）。"""
        return bool(self.wx_appid and self.wx_app_secret)


settings = Settings()
