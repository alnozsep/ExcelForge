"""
app/api/middleware/token_auth.py

トークンベースのアクセス制御。
データベースは使用しない。環境変数から読み込んだ辞書で検証する。
"""

from fastapi import Header, HTTPException, Depends
from app.config import settings


def verify_token(token: str) -> str:
    """
    トークンを検証し、対応する顧客名を返す。

    検証手順:
        1. settings.VALID_TOKENS辞書にトークンが存在するか確認
        2. 存在すれば顧客名を返す
        3. 存在しなければ403 HTTPExceptionを送出

    トークン形式:
        - 英数字のランダム文字列（32文字以上を推奨）
        - secrets.token_urlsafe(32) で生成する

    戻り値: 顧客名（str）
    例外: HTTPException(403)
    """
    if token not in settings.VALID_TOKENS:
        raise HTTPException(
            status_code=403,
            detail="無効なアクセストークンです"
        )
    return settings.VALID_TOKENS[token]
