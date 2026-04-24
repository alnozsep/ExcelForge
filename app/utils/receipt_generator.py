"""
app/utils/receipt_generator.py

証跡レシートの生成。
"""

import uuid
from datetime import datetime, timezone
from app.models.schemas import ProcessingReceipt


def generate_receipt(
    source_hash: str,
    template_hash: str,
    source_type: str,
    source_size: int,
    processing_time: float,
) -> ProcessingReceipt:
    """
    処理結果のレシートを生成する。
    """
    receipt = ProcessingReceipt(
        receipt_id=str(uuid.uuid4()),
        processed_at=datetime.now(timezone.utc),
        source_file_hash=source_hash,
        template_file_hash=template_hash,
        source_file_type=source_type,
        source_file_size_bytes=source_size,
        processing_time_seconds=processing_time,
        gemini_model_used="gemini-1.5-pro-preview-0409",
        data_retention="none",
        storage_used="none",
        database_used="none",
    )

    return receipt
