"""
app/api/endpoints/receipt.py

処理レシートの取得エンドポイント。
レシートはメモリ上のキャッシュであり、Cloud Runインスタンスが停止すると消滅する。
"""

from fastapi import APIRouter, HTTPException
from app.models.schemas import ProcessingReceipt

router = APIRouter()

# メモリ上のレシートキャッシュ（インスタンス単位で保持、永続化しない）
_receipt_cache: dict[str, ProcessingReceipt] = {}


def store_receipt(receipt: ProcessingReceipt) -> None:
    """レシートをメモリキャッシュに保存する"""
    _receipt_cache[receipt.receipt_id] = receipt


@router.get("/receipt/{receipt_id}", response_model=ProcessingReceipt)
async def get_receipt(receipt_id: str):
    """
    GET /api/v1/receipt/{receipt_id}

    処理レシートをJSON形式で取得する。
    receipt_idはレスポンスヘッダに含まれるものと同一。

    注意: レシート自体もメモリ上のキャッシュであり、
          Cloud Runインスタンスが停止すると消滅する。
    """
    if receipt_id not in _receipt_cache:
        raise HTTPException(
            status_code=404,
            detail="指定されたレシートが見つかりません。"
        )
    return _receipt_cache[receipt_id]
