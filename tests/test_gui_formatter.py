"""GUI表示用フォーマッターのユニットテスト -- 6ケース"""

from dataclasses import dataclass, field

import pytest

# パス解決はtests/conftest.pyで実施（GitHub clone/開発環境 両対応）

from vet_dose_calc_gui.gui_formatter import (
    format_calc_for_gui,
    format_suggest_for_gui,
    WARNING_CAT_CONTRA,
    WARNING_NTI,
)
from dosage_calc import DoseResult, ProductAmount


# --- テスト用モックデータ ---

def _make_dose_result(**kwargs) -> DoseResult:
    """DoseResultのテスト用ファクトリ"""
    defaults = {
        "dose_min_mg": 62.5,
        "dose_max_mg": 125.0,
        "indication": "一般感染症",
        "frequency": "BID",
        "route": "PO",
        "duration": "7-14日",
        "notes": "",
    }
    defaults.update(kwargs)
    return DoseResult(**defaults)


def _make_product_amount(**kwargs) -> ProductAmount:
    """ProductAmountのテスト用ファクトリ"""
    defaults = {
        "brand": "クラバモックス小型犬用",
        "strength": 62.5,
        "strength_unit": "mg/tab",
        "amount": 1.0,
        "unit_label": "錠",
        "rounded_amount": None,
    }
    defaults.update(kwargs)
    return ProductAmount(**defaults)


# --- SuggestResult用のモック ---

@dataclass
class MockSuggestProduct:
    brand: str = "テスト商品"
    strength: float = 10.0
    strength_unit: str = "mg/tab"


@dataclass
class MockSuggestReference:
    title: str = "テスト文献"
    url: str = "https://example.com"


@dataclass
class MockSuggestion:
    drug_name_ja: str = "テスト薬"
    drug_name_en: str = "TestDrug"
    category: str = "antibiotics"
    indication: str = "テスト適応"
    species: str = "dog"
    dose_mg_per_kg: str = "10-20"
    frequency: str = "BID"
    route: str = "PO"
    duration: str = "7日"
    products: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    references: list = field(default_factory=list)
    confidence: str = "medium"


@dataclass
class MockSuggestResult:
    suggestions: list = field(default_factory=list)
    grounding_urls: list = field(default_factory=list)
    raw_text: str = ""


class TestFormatCalcForGui:
    """format_calc_for_gui() のテスト"""

    def test_single_indication(self):
        """正常: 単一適応症の基本構造を確認"""
        dr = _make_dose_result()
        pa = _make_product_amount()
        result = format_calc_for_gui(
            drug_name="アモキシシリン",
            species="dog",
            weight_kg=5.0,
            dose_results=[dr],
            product_amounts=[[pa]],
            safety_flags={},
        )
        assert result["drug_name"] == "アモキシシリン"
        assert result["species_label"] == "犬"
        assert result["weight_kg"] == 5.0
        assert len(result["indications"]) == 1
        assert result["indications"][0]["indication"] == "一般感染症"
        assert len(result["indications"][0]["products"]) == 1
        assert result["warnings"] == []
        assert "登録データ" in result["disclaimer"]

    def test_multiple_indications(self):
        """正常: 複数適応症の構造を確認"""
        dr1 = _make_dose_result(indication="一般感染症")
        dr2 = _make_dose_result(
            indication="重症感染",
            dose_min_mg=125.0,
            dose_max_mg=250.0,
        )
        pa1 = _make_product_amount()
        pa2 = _make_product_amount(amount=2.0)
        result = format_calc_for_gui(
            drug_name="テスト薬",
            species="dog",
            weight_kg=10.0,
            dose_results=[dr1, dr2],
            product_amounts=[[pa1], [pa2]],
            safety_flags={},
        )
        assert len(result["indications"]) == 2
        assert result["indications"][0]["indication"] == "一般感染症"
        assert result["indications"][1]["indication"] == "重症感染"

    def test_nti_warning(self):
        """NTI薬フラグでwarningが含まれる"""
        dr = _make_dose_result()
        result = format_calc_for_gui(
            drug_name="ジゴキシン",
            species="dog",
            weight_kg=10.0,
            dose_results=[dr],
            product_amounts=[[]],
            safety_flags={"narrow_therapeutic_index": True},
        )
        assert len(result["warnings"]) == 1
        assert result["warnings"][0]["type"] == "warning"
        assert WARNING_NTI in result["warnings"][0]["message"]

    def test_cat_contraindicated_warning(self):
        """猫禁忌フラグでerror警告が含まれる"""
        dr = _make_dose_result()
        result = format_calc_for_gui(
            drug_name="ペルメトリン",
            species="cat",
            weight_kg=4.0,
            dose_results=[dr],
            product_amounts=[[]],
            safety_flags={"cat_contraindicated": True},
        )
        assert len(result["warnings"]) == 1
        assert result["warnings"][0]["type"] == "error"
        assert WARNING_CAT_CONTRA in result["warnings"][0]["message"]


class TestFormatSuggestForGui:
    """format_suggest_for_gui() のテスト"""

    def test_normal_suggestions(self):
        """正常: 候補リストが正しく変換される"""
        suggestion = MockSuggestion(
            products=[MockSuggestProduct()],
            references=[MockSuggestReference()],
        )
        result_obj = MockSuggestResult(suggestions=[suggestion])

        candidates = format_suggest_for_gui(result_obj)
        assert len(candidates) == 1
        assert candidates[0]["drug_name_ja"] == "テスト薬"
        assert candidates[0]["drug_name_en"] == "TestDrug"
        assert candidates[0]["confidence_level"] == "medium"
        assert candidates[0]["confidence_label"] == "中"
        assert len(candidates[0]["products"]) == 1
        assert len(candidates[0]["references"]) == 1

    def test_empty_suggestions(self):
        """空の候補で空リストが返る"""
        result_obj = MockSuggestResult(suggestions=[])
        candidates = format_suggest_for_gui(result_obj)
        assert candidates == []

    def test_none_result(self):
        """Noneの入力で空リストが返る"""
        candidates = format_suggest_for_gui(None)
        assert candidates == []
