"""导出接口：带领方案 PPT。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from .. import auth, models
from ..db import get_db
from ..ppt import build_ppt
from ..schemas import PptExportRequest

router = APIRouter(prefix="/api/v1", tags=["export"])


@router.post("/export/ppt")
def export_ppt(
    req: PptExportRequest,
    user: models.User | None = Depends(auth.get_current_user_optional),
):
    """生成观电影法带领方案 PPT（.pptx），前端直接下载。"""
    pptx_bytes = build_ppt(req.answers, req.movies)
    return Response(
        content=pptx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": "attachment; filename=guanying_fangan.pptx"},
    )
