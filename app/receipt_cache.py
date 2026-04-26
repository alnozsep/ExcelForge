"""
app/receipt_cache.py

責務: 処理レシートのインメモリキャッシュ（TTL管理付き）。

レシートは処理後すぐにダウンロードされる想定のため、
キャッシュの有効期限は短めに設定している。

Cloud Runの複数インスタンス環境ではインスタンスごとに
独立したキャッシュとなることに注意。
"""

import time
from app.models.schemas import ProcessingReceipt

# レシートのデフォルト有効期限（秒）
DEFAULT_TTL_SECONDS = 300  # 5分

_receipt_cache: dict[str, tuple[ProcessingReceipt, float]] = {}
"""
_cache形式: {receipt_id: (Receiptオブジェクト, 有効期限(Unixタイムスタンプ))}
"""


def store_receipt(
    receipt: ProcessingReceipt, ttl_seconds: int = DEFAULT_TTL_SECONDS
) -> None:
    """
    レシートをメモリキャッシュに保存する。

    Args:
        receipt: 保存するレシート
        ttl_seconds: 有効期限（秒）。デフォルト300秒（5分）。
    """
    expiry = time.time() + ttl_seconds
    _receipt_cache[receipt.receipt_id] = (receipt, expiry)


def get_receipt(receipt_id: str) -> ProcessingReceipt | None:
    """
    レシートを取得する。

    有効期限切れの場合はNoneを返し、キャッシュから削除する。
    """
    entry = _receipt_cache.get(receipt_id)
    if entry is None:
        return None

    receipt, expiry = entry
    if time.time() > expiry:
        # 有効期限切れ: キャッシュから削除
        del _receipt_cache[receipt_id]
        return None

    return receipt


def cleanup_expired() -> int:
    """
    期限切れのレシートをすべて削除する。

    Returns:
        削除したレシートの数
    """
    now = time.time()
    expired_ids = [
        receipt_id for receipt_id, (_, expiry) in _receipt_cache.items() if now > expiry
    ]
    for receipt_id in expired_ids:
        del _receipt_cache[receipt_id]
    return len(expired_ids)
