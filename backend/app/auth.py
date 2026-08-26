"""鉴权：JWT 签发/校验 + 微信 code2session + FastAPI 依赖。

微信「静默登录」流程：
  小程序端 Taro.login() 拿到临时 code → POST /api/v1/auth/wx-login
  → 后端调用微信 jscode2session 换 openid/session_key → 建用户 → 签发 JWT
  → 后续请求携带 Authorization: Bearer <token>。
未配置 WX_APPID/WX_APP_SECRET 时进入开发模式：用 code 派生一个稳定的伪 openid。
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from . import models
from .config import settings
from .db import get_db

bearer_scheme = HTTPBearer(auto_error=False)


# ---------- JWT ----------
def create_token(openid: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": openid,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return payload.get("sub")
    except jwt.PyJWTError:
        return None


# ---------- 微信 code2session ----------
def wechat_code2session(code: str) -> str | None:
    """用临时 code 换取 openid。未配置微信凭证时返回 None（由调用方走开发模式）。"""
    if not settings.wx_enabled:
        return None
    try:
        resp = httpx.get(
            "https://api.weixin.qq.com/sns/jscode2session",
            params={
                "appid": settings.wx_appid,
                "secret": settings.wx_app_secret,
                "js_code": code,
                "grant_type": "authorization_code",
            },
            timeout=10.0,
        )
        data = resp.json()
        return data.get("openid") if "openid" in data else None
    except Exception:  # noqa: BLE001 - 网络异常时回退到开发模式
        return None


def dev_openid(code: str) -> str:
    """开发模式：由 code 派生稳定伪 openid（同一 code 得到同一用户）。"""
    import hashlib

    return "dev_" + hashlib.sha256(f"cinelib:{code}".encode()).hexdigest()[:24]


# ---------- 手机号短信验证码（开发模式：验证码直接返回；生产需接短信服务商） ----------
import random
import time

_sms_codes: dict[str, tuple[str, float]] = {}  # phone -> (code, 过期时间戳)


def sms_send_code(phone: str) -> str:
    """生成 6 位验证码并"发送"。开发模式返回验证码本身。"""
    code = f"{random.randint(0, 999999):06d}"
    _sms_codes[phone] = (code, time.time() + 300)  # 5 分钟有效
    return code


def sms_verify(phone: str, code: str) -> bool:
    rec = _sms_codes.get(phone)
    if not rec:
        return False
    saved, exp = rec
    if time.time() > exp:
        _sms_codes.pop(phone, None)
        return False
    if saved != code:
        return False
    _sms_codes.pop(phone, None)
    return True


# ---------- 公众号 H5 网页授权（OAuth） ----------
def wechat_oauth_authorize_url(redirect_uri: str, state: str, scope: str = "snsapi_base") -> str:
    """构造公众号网页授权跳转地址。"""
    return (
        "https://open.weixin.qq.com/connect/oauth2/authorize"
        f"?appid={settings.wx_appid}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
        f"&scope={scope}"
        f"&state={state}"
        "#wechat_redirect"
    )


def wechat_oauth_code2openid(code: str) -> str | None:
    """公众号网页授权：用 code 换 openid（snsapi_base 静默授权）。

    与小程序 jscode2session 是两套不同的微信接口，这里走 sns/oauth2/access_token。
    """
    if not settings.wx_enabled:
        return None
    try:
        resp = httpx.get(
            "https://api.weixin.qq.com/sns/oauth2/access_token",
            params={
                "appid": settings.wx_appid,
                "secret": settings.wx_app_secret,
                "code": code,
                "grant_type": "authorization_code",
            },
            timeout=10.0,
        )
        data = resp.json()
        return data.get("openid") if "openid" in data else None
    except Exception:  # noqa: BLE001
        return None


# ---------- FastAPI 依赖 ----------
def _resolve_user(creds: HTTPAuthorizationCredentials | None, db: Session) -> models.User | None:
    if creds is None:
        return None
    openid = decode_token(creds.credentials)
    if not openid:
        return None
    return db.query(models.User).filter(models.User.openid == openid).first()


def get_current_user_optional(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> models.User | None:
    """可选鉴权：未登录返回 None（网页版/未登录也能用）。"""
    return _resolve_user(creds, db)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    """强制鉴权：未登录或 token 无效返回 401。"""
    user = _resolve_user(creds, db)
    if user is None:
        raise HTTPException(status_code=401, detail="未登录或登录已过期")
    return user
