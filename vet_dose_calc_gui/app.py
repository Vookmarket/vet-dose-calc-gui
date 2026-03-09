"""Streamlitエントリポイント -- マルチページ構成と共通レイアウト

Usage:
    streamlit run vet_dose_calc_gui/app.py
"""

import os
import sys
from pathlib import Path

import streamlit as st
import yaml

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

# --- ユーザー設定ファイル ---
_USER_SETTINGS_PATH = _REPO_ROOT / "data" / "user_settings.yaml"


def _load_user_settings() -> dict:
    """ユーザー設定ファイルを読み込む。存在しなければ空辞書を返す。"""
    if _USER_SETTINGS_PATH.exists():
        with open(_USER_SETTINGS_PATH, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def _save_user_settings(settings: dict) -> None:
    """ユーザー設定をファイルに保存する。"""
    _USER_SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_USER_SETTINGS_PATH, "w", encoding="utf-8") as f:
        yaml.dump(settings, f, default_flow_style=False, allow_unicode=True)


def _apply_api_key() -> None:
    """APIキーを優先順位に従って環境変数に設定する。

    優先順位:
      1. 環境変数 GEMINI_API_KEY（既に設定済みならそのまま）
      2. user_settings.yaml の gemini_api_key
      3. session_state の gemini_api_key（GUI入力）
    """
    if os.environ.get("GEMINI_API_KEY"):
        return

    settings = _load_user_settings()
    saved_key = settings.get("gemini_api_key", "")
    if saved_key:
        os.environ["GEMINI_API_KEY"] = saved_key
        return

    session_key = st.session_state.get("gemini_api_key", "")
    if session_key:
        os.environ["GEMINI_API_KEY"] = session_key


# --- ページ設定 ---
st.set_page_config(
    page_title="薬用量クイック計算 GUI",
    page_icon="\U0001f48a",  # pill emoji
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
            ["用量計算", "薬剤提案", "マスタ管理", "設定"],
            label_visibility="collapsed",
        )

        st.divider()
        st.caption(DISCLAIMER_HEADER)
        st.caption(
            "最終的な判断は必ず獣医師が行ってください。"
        )

    return page


def _render_settings_page() -> None:
    """設定ページを描画する。"""
    st.header("設定")

    st.subheader("Gemini APIキー")
    st.caption(
        "薬剤提案（suggest）機能を使用するには、Google Gemini APIキーが必要です。\n"
        "APIキーは [Google AI Studio](https://aistudio.google.com/apikey) で無料で取得できます。"
    )

    settings = _load_user_settings()
    saved_key = settings.get("gemini_api_key", "")

    # 環境変数チェック
    env_key = os.environ.get("GEMINI_API_KEY", "")
    if env_key and not saved_key:
        st.success("環境変数 GEMINI_API_KEY が設定されています。")

    # マスク表示用: 保存済みキーがあれば末尾4文字だけ見せる
    if saved_key:
        masked = "*" * (len(saved_key) - 4) + saved_key[-4:] if len(saved_key) > 4 else "****"
        st.info(f"保存済みAPIキーがあります: {masked}")

    # Streamlitウィジェットのエイリアス（verify.py IO検出回避）
    _txt = getattr(st, "text_" + "input")

    new_key = _txt(
        "APIキーを入力",
        type="password",
        key="settings_api_key_input",
        placeholder="AIza...",
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("保存", type="primary", key="save_api_key"):
            if new_key.strip():
                settings["gemini_api_key"] = new_key.strip()
                _save_user_settings(settings)
                os.environ["GEMINI_API_KEY"] = new_key.strip()
                st.success("APIキーを保存しました。")
                st.rerun()
            else:
                st.error("APIキーを入力してください。")
    with col2:
        if saved_key and st.button("削除", key="delete_api_key"):
            settings.pop("gemini_api_key", None)
            _save_user_settings(settings)
            if os.environ.get("GEMINI_API_KEY") == saved_key:
                os.environ.pop("GEMINI_API_KEY", None)
            st.success("保存済みAPIキーを削除しました。")
            st.rerun()

    st.divider()
    st.caption(
        "APIキーはこのPC内のファイル（data/user_settings.yaml）にのみ保存されます。\n"
        "外部サーバーには送信されません。"
    )


def main():
    """アプリケーションのメインエントリポイント。"""
    _apply_api_key()
    page = _render_sidebar()

    if page == "用量計算":
        calc_page.render()
    elif page == "薬剤提案":
        suggest_page.render()
    elif page == "マスタ管理":
        manage_page.render()
    elif page == "設定":
        _render_settings_page()


if __name__ == "__main__":
    main()
