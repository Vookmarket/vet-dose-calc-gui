"""Streamlitエントリポイント -- マルチページ構成と共通レイアウト

Usage:
    streamlit run vet_dose_calc_gui/app.py
"""

import sys
from pathlib import Path

import streamlit as st

# --- パス解決 ---
# 1. 自パッケージ（vet_dose_calc_gui）をimportできるようリポジトリルートを追加
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# 2. VT-004コアモジュールのパス追加（複数候補を順に探索）
#    GitHub clone: vet-dose-calc/vet_dose_calc/dosage_calc.py（パッケージ構造・相対import）
#    開発環境:     VT-004/dosage_calc.py（フラット構造・絶対import）
_PARENT = _REPO_ROOT.parent
_VT004_CANDIDATES = [
    _PARENT / "vet-dose-calc",   # GitHub clone名
    _PARENT / "VT-004",          # 開発環境（tools/VT-004）
    _PARENT / "vet_dose_calc",   # pip editable install
]
_VT004_BARE_MODULES = [
    "dosage_calc", "drug_registry", "input_parser",
    "product_registry", "suggest_engine", "llm_client",
    "output_formatter", "registration_flow", "tool",
]
for _candidate in _VT004_CANDIDATES:
    if not _candidate.is_dir():
        continue
    _inner = _candidate / "vet_dose_calc"
    if _inner.is_dir() and (_inner / "dosage_calc.py").exists():
        # パッケージ構造: リポジトリルートをsys.pathに追加し、
        # bare import用のエイリアスをsys.modulesに登録
        if str(_candidate) not in sys.path:
            sys.path.insert(0, str(_candidate))
        import importlib
        _pkg = importlib.import_module("vet_dose_calc")
        for _mod_name in _VT004_BARE_MODULES:
            if _mod_name not in sys.modules:
                try:
                    sys.modules[_mod_name] = importlib.import_module(
                        f"vet_dose_calc.{_mod_name}"
                    )
                except ImportError:
                    pass
    else:
        # フラット構造: ディレクトリ自体をsys.pathに追加
        if str(_candidate) not in sys.path:
            sys.path.insert(0, str(_candidate))
    break

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
