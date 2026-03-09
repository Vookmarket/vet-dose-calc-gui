"""Streamlitエントリポイント -- マルチページ構成と共通レイアウト

Usage:
    streamlit run vet_dose_calc_gui/app.py
"""

import sys
from pathlib import Path

import streamlit as st

# VT-004のコアモジュールをimportするためパスを追加
_VT004_DIR = Path(__file__).resolve().parent.parent.parent / "VT-004"
if str(_VT004_DIR) not in sys.path:
    sys.path.insert(0, str(_VT004_DIR))

from vet_dose_calc_gui import __version__
from vet_dose_calc_gui.gui_formatter import (
    DISCLAIMER_HEADER,
    DISCLAIMER_SIDEBAR,
)
from vet_dose_calc_gui.pages import calc_page, suggest_page, manage_page


# --- ページ設定 ---
st.set_page_config(
    page_title="薬用量クイック計算 GUI",
    page_icon="💊",
    layout="wide",
)


def _render_sidebar() -> str:
    """サイドバーの共通要素を描画し、選択されたページ名を返す。"""
    with st.sidebar:
        st.title("薬用量クイック計算")
        st.caption(f"v{__version__}")

        st.warning(DISCLAIMER_SIDEBAR)

        page = st.radio(
            "ページ選択",
            ["用量計算", "薬剤提案", "マスタ管理"],
            label_visibility="collapsed",
        )

        st.divider()
        st.caption(DISCLAIMER_HEADER)
        st.caption(
            "最終的な判断は必ず獣医師が行ってください。"
        )

    return page


def main():
    """アプリケーションのメインエントリポイント。"""
    page = _render_sidebar()

    if page == "用量計算":
        calc_page.render()
    elif page == "薬剤提案":
        suggest_page.render()
    elif page == "マスタ管理":
        manage_page.render()


if __name__ == "__main__":
    main()
