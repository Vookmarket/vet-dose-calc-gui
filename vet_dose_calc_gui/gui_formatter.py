"""GUI表示用フォーマッター -- 構造化データをStreamlit表示用に変換

VT-004のコアロジック出力をGUI表示に適した辞書/リストに変換する。
Streamlit固有のAPIは使用せず、pure Pythonで変換のみ行う。
"""

from typing import Any, Optional

# 免責事項定数（VT-004 output_formatterと同一文言）
DISCLAIMER_CALC = (
    "登録データに基づく計算結果です。\n"
    "臨床判断は必ず獣医師が行ってください。"
)

DISCLAIMER_SUGGEST = (
    "AI提案です（参考情報）。臨床判断は獣医師が行ってください。\n"
    "根拠URLで内容を確認することを推奨します。"
)

WARNING_NTI = "治療域が狭い薬剤です。用量を慎重に確認してください。"
WARNING_CAT_CONTRA = "この薬剤は猫に禁忌として登録されています。使用しないでください。"

DISCLAIMER_SIDEBAR = (
    "本ツールは試作品（プロトタイプ）です。\n"
    "実務で使用する場合は、出力内容を必ず専門家が確認してください。"
)

DISCLAIMER_HEADER = (
    "このツールは参考補助を目的としており、"
    "獣医師による診断の代替ではありません。"
)

DISCLAIMER_AI = (
    "このツールの出力にはAIによる生成が含まれます。\n"
    "臨床判断は必ず獣医師が行ってください。"
)

SPECIES_LABELS = {"dog": "犬", "cat": "猫"}

FREQ_LABELS = {
    "SID": "1回/日",
    "BID": "2回/日",
    "TID": "3回/日",
    "QID": "4回/日",
    "EOD": "隔日",
}

FREQ_TO_TIMES = {
    "SID": 1,
    "BID": 2,
    "TID": 3,
    "QID": 4,
}


def format_calc_for_gui(
    drug_name: str,
    species: str,
    weight_kg: float,
    dose_results: list,
    product_amounts: list[list],
    safety_flags: dict,
) -> dict:
    """用量計算結果をGUI表示用辞書に変換する。

    Args:
        drug_name: 薬剤名
        species: 動物種 (dog/cat)
        weight_kg: 体重(kg)
        dose_results: DoseResultのリスト
        product_amounts: 適応症ごとのProductAmountリスト
        safety_flags: 安全フラグ辞書

    Returns:
        GUI表示用辞書
    """
    warnings = _build_warnings(species, safety_flags)

    indications = []
    for idx, dr in enumerate(dose_results):
        products = []
        if idx < len(product_amounts):
            for pa in product_amounts[idx]:
                products.append({
                    "brand": pa.brand,
                    "strength": pa.strength,
                    "strength_unit": pa.strength_unit,
                    "amount": pa.amount,
                    "unit_label": pa.unit_label,
                    "rounded_amount": pa.rounded_amount,
                })

        indications.append({
            "indication": dr.indication or "一般",
            "dose_min_mg": dr.dose_min_mg,
            "dose_max_mg": dr.dose_max_mg,
            "frequency": dr.frequency,
            "route": dr.route,
            "duration": dr.duration,
            "notes": dr.notes,
            "products": products,
        })

    return {
        "drug_name": drug_name,
        "species": species,
        "species_label": SPECIES_LABELS.get(species, species),
        "weight_kg": weight_kg,
        "indications": indications,
        "warnings": warnings,
        "disclaimer": DISCLAIMER_CALC,
    }


def format_suggest_for_gui(suggest_result: Any) -> list[dict]:
    """薬剤提案結果をGUI表示用リストに変換する。

    Args:
        suggest_result: SuggestResult（suggest_engine.SuggestResult）

    Returns:
        候補のリスト。空の場合は空リスト。
    """
    if not suggest_result or not suggest_result.suggestions:
        return []

    candidates = []
    for s in suggest_result.suggestions:
        confidence_marks = {
            "high": ("high", "高"),
            "medium": ("medium", "中"),
            "low": ("low", "低"),
        }
        conf_level, conf_label = confidence_marks.get(
            s.confidence, ("medium", "中")
        )

        products = []
        for p in (s.products or []):
            products.append({
                "brand": p.brand,
                "strength": p.strength,
                "strength_unit": p.strength_unit,
            })

        references = []
        for r in (s.references or []):
            references.append({
                "title": r.title,
                "url": r.url,
            })

        candidates.append({
            "drug_name_ja": s.drug_name_ja,
            "drug_name_en": s.drug_name_en,
            "category": s.category,
            "indication": s.indication,
            "dose_mg_per_kg": s.dose_mg_per_kg,
            "frequency": s.frequency,
            "route": s.route,
            "duration": s.duration,
            "products": products,
            "warnings": s.warnings or [],
            "references": references,
            "confidence_level": conf_level,
            "confidence_label": conf_label,
        })

    return candidates


def _build_warnings(species: str, safety_flags: dict) -> list[dict]:
    """安全フラグからwarningリストを構築する。

    Returns:
        [{"type": "error"|"warning", "message": str}, ...]
    """
    warnings = []
    if safety_flags.get("cat_contraindicated") and species == "cat":
        warnings.append({
            "type": "error",
            "message": WARNING_CAT_CONTRA,
        })
    if safety_flags.get("narrow_therapeutic_index"):
        warnings.append({
            "type": "warning",
            "message": WARNING_NTI,
        })
    return warnings
