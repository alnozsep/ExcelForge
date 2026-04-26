"""
streamlit_app/pages/upload.py

アップロード画面。ファイルの検証とAPI呼び出しを行う。
処理エンジンは同一プロセス内で直接呼び出す（FastAPIプロセスの分離不要）。
"""

import streamlit as st
import json
import sys
from pathlib import Path
import asyncio

st.set_page_config(page_title="アップロード - ExcelForge", page_icon="🤖")

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

from app.processing_flow import run_processing  # noqa: E402


def main():
    # 認証チェック
    if not st.session_state.get("is_authenticated"):
        st.error("認証されていません。トップページからアクセスしてください。")
        st.switch_page("home.py")
        return

    render_header()

    st.markdown("### ファイルアップロード")

    st.markdown("---")
    st.markdown("#### ⚙ 設定")

    # 処理モードの説明
    mode_descriptions = {
        "AI自動判定 (Auto)": "AIがテンプレートの構造を読み取り、最適なセルを自動的に判断してデータを転記します。テンプレートに設定が不要な最も手軽なモードです。",
        "プレースホルダーのみ (Placeholder)": "テンプレート内の `{{項目名}}` という記述のみを置換対象にします。AIにはテンプレート構造を伝えないため、意図しない場所への書き込みを完全に防げます。",
        "マニュアル指定 (Manual)": "どの項目をどのセル（例: A1）に書き込むかをJSON形式で厳密に指定します。定型業務で転記先を固定したい場合に最適です。",
    }

    processing_mode = st.radio(
        "処理モードを選択してください",
        list(mode_descriptions.keys()),
        index=0,
        help="用途に合わせてAIの挙動を切り替えます。",
    )

    st.info(mode_descriptions[processing_mode])

    mapping_config_input = ""
    if processing_mode == "マニュアル指定 (Manual)":
        mapping_config_input = st.text_area(
            "マッピング設定 (JSON)",
            placeholder="""{\n  "mappings": [\n    {"key": "会社名", "sheet": "Sheet1", "cell": "A1"},\n    {"key": "合計金額", "sheet": "Sheet1", "cell": "G30"}\n  ]\n}""",
            height=200,
            help="書き込み先のシート名とセル番地を明示的に指定してください。",
        )

    st.markdown("---")

    # 変換実行ボタン（ファイル選択とボタンのみフォーム内に配置）
    with st.form("upload_form"):
        st.markdown("#### 📄 ファイル選択")
        source_file = st.file_uploader(
            "ソースファイル（PDF, CSV, Excel）",
            type=["pdf", "csv", "xlsx", "xls"],
            key="source_file",
        )
        template_file = st.file_uploader(
            "Excelテンプレート（.xlsx）",
            type=["xlsx"],
            key="template_file",
        )

        st.info("⚠ アップロードされたファイルは処理後即座に削除されます。")

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
            "マニュアル指定 (Manual)": "manual",
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
            st.write("ファイルを読み込み、AIがデータを抽出しています...")
            st.write("※ 通常1〜3分程度で完了します")

            try:
                source_bytes = source_file.getvalue()
                template_bytes = template_file.getvalue()

                # 処理エンジンを直接呼び出す（asyncio.run で非同期実行）
                output_buffer, receipt_data = asyncio.run(
                    run_processing(
                        source_bytes=source_bytes,
                        template_bytes=template_bytes,
                        source_filename=source_file.name,
                        mapping_config=mapping_config_input
                        if api_mode == "manual"
                        else None,
                        processing_mode=api_mode,
                    )
                )

                status.update(label="変換完了", state="complete", expanded=False)

                # 結果をセッションステートに保存
                st.session_state.result_excel = output_buffer.getvalue()
                st.session_state.receipt_data = receipt_data

                st.switch_page("pages/result.py")

            except Exception as e:
                status.update(
                    label="エラーが発生しました", state="error", expanded=False
                )
                st.error(f"処理中にエラーが発生しました: {e}")

    render_footer()


if __name__ == "__main__":
    main()
