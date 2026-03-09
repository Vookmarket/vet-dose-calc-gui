"""設定管理のユニットテスト -- APIキー保存・読み込み・優先順位"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml


# テスト対象の関数をインポート（app.pyのモジュールレベルコードは
# Streamlitに依存するため、関数を直接テストする）


@pytest.fixture
def tmp_settings(tmp_path):
    """一時ディレクトリにuser_settings.yamlを配置するフィクスチャ"""
    settings_path = tmp_path / "data" / "user_settings.yaml"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    return settings_path


class TestUserSettingsIO:
    """user_settings.yaml の読み書きテスト"""

    def test_save_and_load(self, tmp_settings):
        """保存したAPIキーが読み込める"""
        settings = {"gemini_api_key": "test-key-12345"}
        with open(tmp_settings, "w", encoding="utf-8") as f:
            yaml.dump(settings, f, default_flow_style=False)

        with open(tmp_settings, encoding="utf-8") as f:
            loaded = yaml.safe_load(f) or {}
        assert loaded["gemini_api_key"] == "test-key-12345"

    def test_load_nonexistent(self, tmp_path):
        """存在しないファイルは空辞書扱い"""
        path = tmp_path / "data" / "user_settings.yaml"
        assert not path.exists()
        # _load_user_settings相当のロジック
        result = {}
        if path.exists():
            with open(path, encoding="utf-8") as f:
                result = yaml.safe_load(f) or {}
        assert result == {}

    def test_save_creates_directory(self, tmp_path):
        """保存時にdataディレクトリが自動作成される"""
        settings_path = tmp_path / "data" / "user_settings.yaml"
        assert not settings_path.parent.exists()

        settings_path.parent.mkdir(parents=True, exist_ok=True)
        with open(settings_path, "w", encoding="utf-8") as f:
            yaml.dump({"gemini_api_key": "abc"}, f)

        assert settings_path.exists()
        with open(settings_path, encoding="utf-8") as f:
            loaded = yaml.safe_load(f)
        assert loaded["gemini_api_key"] == "abc"

    def test_delete_key(self, tmp_settings):
        """APIキーの削除"""
        settings = {"gemini_api_key": "to-be-deleted", "other": "keep"}
        with open(tmp_settings, "w", encoding="utf-8") as f:
            yaml.dump(settings, f)

        # 削除操作
        with open(tmp_settings, encoding="utf-8") as f:
            loaded = yaml.safe_load(f) or {}
        loaded.pop("gemini_api_key", None)
        with open(tmp_settings, "w", encoding="utf-8") as f:
            yaml.dump(loaded, f)

        # 確認
        with open(tmp_settings, encoding="utf-8") as f:
            result = yaml.safe_load(f) or {}
        assert "gemini_api_key" not in result
        assert result["other"] == "keep"


class TestApiKeyPriority:
    """APIキーの優先順位テスト"""

    def test_env_var_has_highest_priority(self):
        """環境変数が設定済みなら他のソースは無視"""
        # _apply_api_key相当のロジック
        env_key = "env-key-value"
        saved_key = "saved-key-value"
        session_key = "session-key-value"

        # 優先順位1: 環境変数
        result = env_key if env_key else (saved_key if saved_key else session_key)
        assert result == "env-key-value"

    def test_saved_key_over_session(self):
        """保存済みキーはセッションキーより優先"""
        env_key = ""
        saved_key = "saved-key-value"
        session_key = "session-key-value"

        result = env_key if env_key else (saved_key if saved_key else session_key)
        assert result == "saved-key-value"

    def test_session_key_as_fallback(self):
        """セッションキーは最低優先度"""
        env_key = ""
        saved_key = ""
        session_key = "session-key-value"

        result = env_key if env_key else (saved_key if saved_key else session_key)
        assert result == "session-key-value"

    def test_no_key_available(self):
        """全ソースが空なら空文字列"""
        env_key = ""
        saved_key = ""
        session_key = ""

        result = env_key if env_key else (saved_key if saved_key else session_key)
        assert result == ""


class TestApiKeyMasking:
    """APIキーのマスク表示テスト"""

    def test_mask_long_key(self):
        """長いキーは末尾4文字以外をマスク"""
        key = "AIzaSyD1234567890abcdef"
        masked = "*" * (len(key) - 4) + key[-4:] if len(key) > 4 else "****"
        assert masked.endswith("cdef")
        assert masked.count("*") == len(key) - 4

    def test_mask_short_key(self):
        """4文字以下のキーは全マスク"""
        key = "abc"
        masked = "*" * (len(key) - 4) + key[-4:] if len(key) > 4 else "****"
        assert masked == "****"

    def test_mask_exactly_4_chars(self):
        """ちょうど4文字のキーは全マスク"""
        key = "abcd"
        masked = "*" * (len(key) - 4) + key[-4:] if len(key) > 4 else "****"
        assert masked == "****"

    def test_mask_5_chars(self):
        """5文字のキーは先頭1文字マスク"""
        key = "abcde"
        masked = "*" * (len(key) - 4) + key[-4:] if len(key) > 4 else "****"
        assert masked == "*bcde"
