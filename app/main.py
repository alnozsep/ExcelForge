"""
app/main.py

FastAPIアプリケーションのエントリーポイント。
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import logging

from app.config import settings
from app.models.enums import AppException, ErrorCode
from app.models.schemas import TokenValidationRequest, TokenValidationResponse
from app.api.router import api_router
from app.api.middleware.token_auth import verify_token

# ログ設定
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format=settings.LOG_FORMAT
)
logger = logging.getLogger("excelforge")

app = FastAPI(title="ExcelForge API", version=settings.APP_VERSION)

# ルーターをマウント
app.include_router(api_router)


# === エラーハンドラ ===

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.message,
            "error_code": exc.error_code.value,
            "retry_suggestion": exc.error_code in [
                ErrorCode.EXTRACTION_FAILED,
                ErrorCode.TIMEOUT
            ]
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    # 予期せぬエラー。ログに記録するがユーザーデータは含めない。
    logger.error(f"Unexpected error: {type(exc).__name__}: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "内部サーバーエラーが発生しました",
            "error_code": ErrorCode.INTERNAL_ERROR.value,
            "retry_suggestion": False
        }
    )


# === トークン検証エンドポイント（設計書 6.2） ===

@app.post("/api/v1/validate-token", response_model=TokenValidationResponse)
async def validate_token(request: TokenValidationRequest):
    """
    POST /api/v1/validate-token

    アクセストークンの有効性を検証する。
    """
    if request.token in settings.VALID_TOKENS:
        return TokenValidationResponse(
            valid=True,
            customer_name=settings.VALID_TOKENS[request.token]
        )
    return TokenValidationResponse(valid=False)
