"""
streamlit_app/components/footer.py

共通フッターコンポーネント。
"""

import streamlit as st


def render_footer():
    st.markdown(
        """
        <div style="margin-top: 4rem; padding-top: 2rem; border-top: 1px solid #E2E8F0; text-align: center; color: #94A3B8; font-size: 0.875rem;">
            &copy; 2025 ExcelForge. All rights reserved.
            <br>
            <span style="font-size: 0.75rem;">
                本システムはアップロードされたデータを処理後、即座に破棄します。
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )
