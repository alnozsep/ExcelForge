"""
streamlit_app/home.py

Streamlitアプリケーションのエントリーポイント。
トークンの検証を行い、問題なければアップロード画面へ遷移する。

注意: 処理エンジンは同一プロセス内で直接呼び出すため、
FastAPIプロセスの分離は不要。トークン検証もローカルで行う。
"""

import streamlit as st
import sys
from pathlib import Path

# Streamlitページ設定
st.set_page_config(
    page_title="ExcelForge",
    page_icon="🤖",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# プロジェクトルートを検索パスに追加
project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

try:
    from streamlit_app.components.header import render_header
    from streamlit_app.components.footer import render_footer
except ImportError:
    from components.header import render_header  # type: ignore
    from components.footer import render_footer  # type: ignore

from app.config import settings  # noqa: E402


def main():
    render_header()

    # クエリパラメータからトークンを取得
    # 注意: クエリパラメータ経由のトークン送信は、
    # ブラウザ履歴・リファラ・サーバーアクセスログに残る可能性がある。
    # よりセキュアな方法として、POSTボディやAuthorizationヘッダーの利用を検討すること。
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
            # ローカルでトークン検証（FastAPIエンドポイントへのHTTP呼び出し不要）
            if token in settings.VALID_TOKENS:
                st.session_state.is_authenticated = True
                st.session_state.token = token
                st.session_state.customer_name = settings.VALID_TOKENS[token]
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
