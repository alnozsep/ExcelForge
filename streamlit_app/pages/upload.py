"""
streamlit_app/pages/upload.py

アップロード画面。ファイルの検証とAPI呼び出しを行う。
"""

import streamlit as st
import httpx
import os
import json

import sys
from pathlib import Path

# プロジェクトルートを検索パスに追加
project_root = str(Path(__file__).resolve().parent.parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

try:
    from streamlit_app.components.header import render_header
    from streamlit_app.components.footer import render_footer
except ImportError:
    from components.header import render_header
    from components.footer import render_footer

st.set_page_config(page_title="アップロード - ExcelForge", page_icon="🤖")

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8080/api/v1")


def main():
    # 認証チェック
    if not st.session_state.get("is_authenticated"):
        st.error("認証されていません。トップページからアクセスしてください。")
        st.switch_page("app.py")
        return

    render_header()

    st.markdown("### ファイルアップロード")

    # フォーム開始
    with st.form("upload_form"):
        st.markdown("#### 📄 ソースファイル")
        source_file = st.file_uploader(
            "ここにファイルをドラッグ&ドロップ または クリックして選択",
            type=["pdf", "csv", "xlsx", "xls"],
            key="source_file",
        )
        st.caption("対応形式: PDF, CSV, Excel (.xlsx/.xls) | 最大サイズ: 10MB")

        st.markdown("#### 📋 Excelテンプレート")
        template_file = st.file_uploader(
            "ここにファイルをドラッグ&ドロップ または クリックして選択",
            type=["xlsx"],
            key="template_file",
        )
        st.caption("対応形式: Excel (.xlsx) | 最大サイズ: 10MB")

        st.markdown("#### ⚙ 設定")
        processing_mode = st.radio(
            "処理モード",
            ["AI自動判定 (Auto)", "プレースホルダーのみ (Placeholder)", "マニュアル指定 (Manual)"],
            index=0,
            help="Auto: AIがテンプレートを解析して自動で書き込みます。Placeholder: テンプレート内の {{key}} のみを置換します。Manual: JSON形式でマッピングを直接指定します。",
        )
        
        mapping_config_input = ""
        if processing_mode == "マニュアル指定 (Manual)":
            mapping_config_input = st.text_area(
                "マッピング設定 (JSON)",
                placeholder='{"mappings": [{"key": "会社名", "sheet": "Sheet1", "cell": "A1"}]}',
                height=150
            )

        st.info(
            "⚠ アップロードされたファイルは処理後即座に削除されます。サーバーには保存されません。"
        )

        submit_btn = st.form_submit_button(
            "▶ 変換を開始する", type="primary", use_container_width=True
        )

    if submit_btn:
        if not source_file or not template_file:
            st.error(
                "ソースファイルとテンプレートファイルの両方をアップロードしてください。"
            )
            return

        # モード変換
        mode_map = {
            "AI自動判定 (Auto)": "auto",
            "プレースホルダーのみ (Placeholder)": "placeholder",
            "マニュアル指定 (Manual)": "manual"
        }
        api_mode = mode_map[processing_mode]

        # JSONバリデーション
        if api_mode == "manual":
            if not mapping_config_input.strip():
                st.error("マニュアル指定モードではJSONマッピングが必要です。")
                return
            try:
                json.loads(mapping_config_input)
            except json.JSONDecodeError:
                st.error("入力されたマッピング設定が有効なJSONではありません。")
                return

        # クライアント側バリデーション
        MAX_SIZE = 10 * 1024 * 1024
        if source_file.size > MAX_SIZE:
            st.error("ソースファイルのサイズが10MBを超えています。")
            return
        if template_file.size > MAX_SIZE:
            st.error("テンプレートファイルのサイズが10MBを超えています。")
            return

        # 処理開始
        with st.status("処理中です...", expanded=True) as status:
            st.write("ファイルをアップロードし、AIがデータを抽出しています...")
            st.write("※ 通常1〜3分程度で完了します")

            try:
                # タイムアウトは長めに設定 (gemini呼び出しがあるため)
                timeout = httpx.Timeout(180.0)

                files = {
                    "source_file": (
                        source_file.name,
                        source_file.getvalue(),
                        "application/octet-stream",
                    ),
                    "template_file": (
                        template_file.name,
                        template_file.getvalue(),
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    ),
                }
                data = {
                    "token": st.session_state.token,
                    "processing_mode": api_mode,
                    "mapping_config": mapping_config_input if api_mode == "manual" else None
                }

                # APIリクエスト
                response = httpx.post(
                    f"{API_BASE_URL}/process", data=data, files=files, timeout=timeout
                )

                if response.status_code == 200:
                    status.update(label="変換完了", state="complete", expanded=False)
                    # 結果をセッションステートに保存して画面遷移
                    st.session_state.result_excel = response.content

                    receipt_str = response.headers.get("X-ExcelForge-Receipt")
                    if receipt_str:
                        st.session_state.receipt_data = json.loads(receipt_str)
                    else:
                        st.session_state.receipt_data = None

                    st.switch_page("pages/result.py")
                else:
                    status.update(
                        label="エラーが発生しました", state="error", expanded=False
                    )
                    try:
                        err_data = response.json()
                        st.error(
                            f"エラー: {err_data.get('detail', '不明なエラー')} (Code: {err_data.get('error_code', '')})"
                        )
                    except Exception:
                        st.error(
                            f"サーバーエラーが発生しました (HTTP {response.status_code})"
                        )
            except httpx.ReadTimeout:
                status.update(label="タイムアウト", state="error", expanded=False)
                st.error(
                    "処理がタイムアウトしました。サーバーの負荷が高いか、データが大きすぎます。"
                )
            except Exception as e:
                status.update(label="通信エラー", state="error", expanded=False)
                st.error(f"APIサーバーとの通信に失敗しました: {e}")

    render_footer()


if __name__ == "__main__":
    main()
