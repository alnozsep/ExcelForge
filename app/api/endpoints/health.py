"""
app/api/endpoints/health.py

ヘルスチェックエンドポイント。認証不要。
"""

from datetime import datetime, timezone
from fastapi import APIRouter
from app.models.schemas import HealthResponse
from app.config import settings

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    GET /api/v1/health

    サーバーの稼働状態を確認する。認証不要。
    """
    return HealthResponse(
        status="healthy",
        version=settings.APP_VERSION,
        timestamp=datetime.now(timezone.utc)
    )
