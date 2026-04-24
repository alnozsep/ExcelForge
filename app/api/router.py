"""
app/api/router.py

APIルーティング定義。全エンドポイントを /api/v1 配下にマウントする。
"""

from fastapi import APIRouter
from app.api.endpoints import health, process, receipt

api_router = APIRouter(prefix="/api/v1")

# ヘルスチェック（認証不要）
api_router.include_router(health.router, tags=["health"])

# メイン処理
api_router.include_router(process.router, tags=["process"])

# レシート
api_router.include_router(receipt.router, tags=["receipt"])
