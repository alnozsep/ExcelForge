"""
streamlit_app/components/header.py

共通ヘッダーコンポーネント。
"""

import streamlit as st

def render_header():
    st.markdown(
        """
        <div style="display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #E2E8F0; padding-bottom: 1rem; margin-bottom: 2rem;">
            <h1 style="margin: 0; font-size: 1.5rem; color: #1E293B;">ExcelForge</h1>
            <span style="font-size: 0.875rem; color: #64748B;">AI自動転記ツール</span>
        </div>
        """,
        unsafe_allow_html=True
    )
