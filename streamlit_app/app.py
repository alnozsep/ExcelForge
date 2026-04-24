"""
streamlit_app/app.py

Streamlitアプリケーションのエントリーポイント。
トークンの検証を行い、問題なければアップロード画面へ遷移する。
"""

import streamlit as st
import httpx
import os

# Streamlitページ設定
st.set_page_config(
    page_title="ExcelForge",
    page_icon="🤖",
    layout="centered",
    initial_sidebar_state="collapsed",
)

from components.header import render_header  # noqa: E402
from components.footer import render_footer  # noqa: E402

# 内部APIエンドポイント（Cloud Runの場合は環境変数等で指定可能にする）
# デフォルトはローカル
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8080/api/v1")


def validate_token(token: str) -> dict:
    """FastAPIのvalidate-tokenエンドポイントを叩く"""
    try:
        response = httpx.post(
            f"{API_BASE_URL}/validate-token", json={"token": token}, timeout=10.0
        )
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        st.error(f"認証サーバーに接続できません: {e}")
    return {"valid": False}


def main():
    render_header()

    # クエリパラメータからトークンを取得
    query_params = st.query_params
    token = query_params.get("token")

    if not token:
        st.error("トークンが指定されていません。正しいURLからアクセスしてください。")
        render_footer()
        return

    # セッションステートに認証済みかどうかのフラグ
    if (
        "is_authenticated" not in st.session_state
        or st.session_state.get("token") != token
    ):
        with st.spinner("認証情報を確認しています..."):
            auth_res = validate_token(token)
            if auth_res.get("valid"):
                st.session_state.is_authenticated = True
                st.session_state.token = token
                st.session_state.customer_name = auth_res.get("customer_name")
            else:
                st.session_state.is_authenticated = False
                st.session_state.token = None

    if st.session_state.get("is_authenticated"):
        # 認証成功したら自動的にアップロード画面へ遷移（ページナビゲーション）
        st.success(f"認証成功: ようこそ {st.session_state.customer_name} 様")
        st.switch_page("pages/upload.py")
    else:
        st.error("無効なアクセストークンです。")

    render_footer()


if __name__ == "__main__":
    main()
