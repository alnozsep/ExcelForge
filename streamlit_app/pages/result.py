"""
streamlit_app/pages/result.py

処理結果・ダウンロード画面。
"""

import streamlit as st
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
    from components.header import render_header  # type: ignore
    from components.footer import render_footer  # type: ignore

st.set_page_config(page_title="処理結果 - ExcelForge", page_icon="✅")


def reset_and_go_back():
    """セッション状態をクリアしてアップロード画面に戻る"""
    # 処理関連のデータを削除（制約: 処理完了後、session_stateから処理関連データを削除する）
    if "result_excel" in st.session_state:
        del st.session_state["result_excel"]
    if "receipt_data" in st.session_state:
        del st.session_state["receipt_data"]

    st.switch_page("pages/upload.py")


def main():
    # 認証チェック
    if not st.session_state.get("is_authenticated"):
        st.error("認証されていません。トップページからアクセスしてください。")
        st.switch_page("app.py")
        return

    # 結果データが存在しない場合はアップロード画面に戻る
    if "result_excel" not in st.session_state:
        st.warning("処理結果が見つかりません。")
        st.switch_page("pages/upload.py")
        return

    render_header()

    st.success("✅ 変換が完了しました！")

    receipt = st.session_state.get("receipt_data", {})
    processing_time = receipt.get("processing_time_seconds", 0)

    if processing_time:
        st.write(f"**処理時間:** {processing_time:.2f} 秒")

    st.markdown("---")

    # ダウンロードセクション
    col1, col2 = st.columns(2)

    with col1:
        st.download_button(
            label="📥 Excelをダウンロード",
            data=st.session_state.result_excel,
            file_name="excelforge_output.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            use_container_width=True,
        )

    with col2:
        if receipt:
            receipt_json = json.dumps(receipt, indent=2, ensure_ascii=False)
            st.download_button(
                label="📋 処理レシートをダウンロード",
                data=receipt_json,
                file_name=f"receipt_{receipt.get('receipt_id', 'unknown')}.json",
                mime="application/json",
                use_container_width=True,
            )

    st.markdown("---")

    st.info(
        "⚠ これはAIによる自動転記結果です。必ずダウンロードして内容をご確認ください。"
    )

    st.button(
        "🔄 別のファイルを処理する",
        on_click=reset_and_go_back,
        use_container_width=True,
    )

    render_footer()


if __name__ == "__main__":
    main()
