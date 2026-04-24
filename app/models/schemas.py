"""
app/models/schemas.py

すべてのリクエスト/レスポンスの型を定義する。
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


# === リクエスト ===


class TokenValidationRequest(BaseModel):
    token: str = Field(..., min_length=10, max_length=100)


# === レスポンス ===


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: datetime


class TokenValidationResponse(BaseModel):
    valid: bool
    customer_name: Optional[str] = None


class ProcessingReceipt(BaseModel):
    receipt_id: str
    processed_at: datetime
    source_file_hash: str
    template_file_hash: str
    source_file_type: str
    source_file_size_bytes: int
    processing_time_seconds: float
    gemini_model_used: str
    data_retention: str = "none"
    storage_used: str = "none"
    database_used: str = "none"


class ErrorResponse(BaseModel):
    detail: str
    error_code: str
    retry_suggestion: bool = False


# === 内部用 ===


class ExtractionResult(BaseModel):
    """Gemini APIからの抽出結果を格納する"""

    data: dict
    raw_response: str = Field(exclude=True)  # ログに出さない
    model_used: str
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None


class MappingConfig(BaseModel):
    """抽出項目とExcelセルの対応定義"""

    mappings: list[dict] = Field(
        ..., description="各要素は {key: str, sheet: str, cell: str} の形式"
    )
