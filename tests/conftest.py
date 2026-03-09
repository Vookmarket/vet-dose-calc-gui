"""pytest設定 -- VT-004パス解決（GitHub clone/開発環境 両対応）"""

import importlib
import sys
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent

# VT-005パッケージをインポート可能にする
if str(_BASE) not in sys.path:
    sys.path.insert(0, str(_BASE))

# VT-004コアモジュールのパス解決（app.pyと同一ロジック）
_PARENT = _BASE.parent
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
        # パッケージ構造: リポジトリルートを追加 + bare importエイリアス登録
        if str(_candidate) not in sys.path:
            sys.path.insert(0, str(_candidate))
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
        # フラット構造: ディレクトリ自体を追加
        if str(_candidate) not in sys.path:
            sys.path.insert(0, str(_candidate))
    break
