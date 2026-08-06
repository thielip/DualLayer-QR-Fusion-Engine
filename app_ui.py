"""Streamlit Cloud entry — keep this file tiny so boot errors stay visible."""

from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="Dual-Layer QR Fusion Engine",
    page_icon="🔲",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.caption("正在載入引擎…（若失敗會顯示紅色錯誤，不是你的操作問題）")

try:
    from app_main import main

    main()
except Exception as exc:
    st.error(
        "雲端啟動失敗——不是你的操作問題。請把下方紅色英文錯誤整段複製傳給開發者。"
    )
    st.exception(exc)
