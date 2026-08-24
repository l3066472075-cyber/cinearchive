"""微信静默登录接口（小程序 code2session + 公众号 H5 网页授权 OAuth）。"""
from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import quote

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from .. import auth, models
from ..config import settings
from ..db import get_db
from ..schemas import MeResponse, WxLoginRequest, WxLoginResponse

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _get_or_create_user(db: Session, openid: str) -> tuple[models.User, bool]:
    """按 openid 取用户，不存在则创建。返回 (user, is_new)。"""
    user = db.query(models.User).filter(models.User.openid == openid).first()
    if user is None:
        user = models.User(openid=openid)
        db.add(user)
        db.flush()
        return user, True
    user.last_login_at = datetime.now(timezone.utc)
    return user, False


@router.post("/wx-login", response_model=WxLoginResponse)
def wx_login(req: WxLoginRequest, db: Session = Depends(get_db)):
    """小程序静默登录：Taro.login() 的 code → openid → 建用户 → 签发 JWT。"""
    openid = auth.wechat_code2session(req.code)
    wx_enabled = settings.wx_enabled
    if openid is None:
        openid = auth.dev_openid(req.code)  # 开发模式回退

    user, is_new = _get_or_create_user(db, openid)
    if req.nickname:
        user.nickname = req.nickname
    if req.avatar_url:
        user.avatar_url = req.avatar_url
    db.commit()
    db.refresh(user)

    return WxLoginResponse(
        token=auth.create_token(openid),
        openid=openid,
        is_new_user=is_new,
        wx_enabled=wx_enabled,
    )


def _callback_url(request: Request) -> str:
    if settings.mp_oauth_redirect_uri:
        return settings.mp_oauth_redirect_uri
    return str(request.url_for("mp_callback"))


@router.get("/mp/authorize", include_in_schema=False)
def mp_authorize(request: Request, redirect_uri: str, scope: str = "snsapi_base"):
    """公众号 H5 静默登录入口：跳转到微信网页授权页（snsapi_base 无需用户确认）。"""
    if settings.wx_enabled:
        url = auth.wechat_oauth_authorize_url(
            _callback_url(request), state=redirect_uri, scope=scope
        )
        return RedirectResponse(url)
    # 开发模式：直接跳到回调，模拟微信的回跳，便于本地联调
    dev = f"/api/v1/auth/mp/callback?code=dev_{int(datetime.now().timestamp())}&state={quote(redirect_uri)}"
    return RedirectResponse(dev)


@router.get("/mp/callback", name="mp_callback", include_in_schema=False)
def mp_callback(code: str, state: str = "", db: Session = Depends(get_db)):
    """微信网页授权回调：code → openid → 建用户 → 签发 JWT → 回跳前端。"""
    openid = auth.wechat_oauth_code2openid(code)
    if openid is None:
        openid = auth.dev_openid(code)  # 开发模式回退

    user, _ = _get_or_create_user(db, openid)
    db.commit()
    token = auth.create_token(openid)

    sep = "&" if "?" in state else "?"
    return RedirectResponse(f"{state}{sep}token={token}")


@router.get("/me", response_model=MeResponse)
def me(user: models.User = Depends(auth.get_current_user)):
    """当前登录用户信息（需要 Bearer token）。"""
    return MeResponse(
        id=user.id,
        openid=user.openid,
        nickname=user.nickname,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )
