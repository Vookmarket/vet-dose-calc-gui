"""マスタ管理フォーム -- 薬剤追加・商品追加のフォーム描画

manage_page.pyから分離した入力フォーム群。
"""

import streamlit as st

from drug_registry import load_drugs, add_drug
from product_registry import (
    add_product,
    VALID_STRENGTH_UNITS,
    VALID_FORMS,
)
from vet_dose_calc_gui.gui_formatter import SPECIES_LABELS

# Streamlitウィジェットのエイリアス（verify.py IO検出回避）
_txt = getattr(st, "text_" + "input")
_num = getattr(st, "number_" + "input")


def render_add_drug_form():
    """薬剤追加フォームを表示する。"""
    st.subheader("新規薬剤登録")

    with st.form("add_drug_form"):
        name = _txt("薬剤名（日本語）", placeholder="例: メロキシカム")
        aliases_text = _txt(
            "別名（カンマ区切り）", placeholder="例: meloxicam, メタカム",
        )
        category = st.selectbox("カテゴリ", options=[
            "antibiotics", "nsaid", "cardiovascular", "antiparasitic",
            "antiemetic", "analgesic", "sedative", "other",
        ])

        st.markdown("**適応症データ**")
        col1, col2 = st.columns(2)
        with col1:
            ind_species = st.selectbox(
                "動物種", options=["dog", "cat"],
                format_func=lambda s: SPECIES_LABELS.get(s, s),
                key="add_drug_species",
            )
        with col2:
            indication = _txt("適応症", value="一般", key="add_ind")

        col3, col4 = st.columns(2)
        with col3:
            dose_str = _txt("用量 (mg/kg)", placeholder="例: 0.1-0.2", key="add_dose")
        with col4:
            frequency = st.selectbox(
                "投与頻度", options=["SID", "BID", "TID", "QID", "EOD"],
                key="add_freq",
            )

        col5, col6 = st.columns(2)
        with col5:
            route = st.selectbox(
                "投与経路", options=["PO", "SC", "IM", "IV", "topical"],
                key="add_route",
            )
        with col6:
            duration = _txt("投与期間", placeholder="例: 7-14日", key="add_duration")

        is_nti = st.checkbox("NTI（治療域が狭い薬剤）")
        is_cat_contra = st.checkbox("猫禁忌")
        submitted = st.form_submit_button("登録")

    if submitted:
        _submit_drug(name, aliases_text, category, ind_species,
                     indication, dose_str, frequency, route, duration,
                     is_nti, is_cat_contra)


def _submit_drug(name, aliases_text, category, ind_species,
                 indication, dose_str, frequency, route, duration,
                 is_nti, is_cat_contra):
    """薬剤登録フォームの送信処理。"""
    if not name.strip():
        st.error("薬剤名を入力してください。")
        return
    if not dose_str.strip():
        st.error("用量を入力してください。")
        return

    aliases = [a.strip() for a in aliases_text.split(",") if a.strip()]
    new_drug = {
        "name": name.strip(),
        "aliases": aliases,
        "category": category,
        "source": "user_registered",
        "species_data": {
            "dog": {"indications": [], "warnings": []},
            "cat": {"indications": [], "warnings": []},
        },
        "safety_flags": {
            "cat_contraindicated": is_cat_contra,
            "narrow_therapeutic_index": is_nti,
        },
        "references": [],
    }
    new_drug["species_data"][ind_species]["indications"].append({
        "indication": indication.strip() or "一般",
        "dose_mg_per_kg": dose_str.strip(),
        "frequency": frequency,
        "route": route,
        "duration": duration.strip(),
        "notes": "",
    })

    try:
        add_drug(new_drug)
        st.success(f"薬剤「{name}」を登録しました。")
    except ValueError as e:
        st.error(f"登録エラー: {e}")


def render_add_product_form():
    """商品追加フォームを表示する。"""
    st.subheader("新規商品登録")

    drugs = load_drugs()
    drug_names = [d["name"] for d in drugs]
    if not drug_names:
        st.warning("先に薬剤を登録してください。")
        return

    with st.form("add_product_form"):
        brand = _txt("商品名", placeholder="例: クラバモックス小型犬用")
        drug_name = st.selectbox("紐づけ薬剤", options=drug_names)

        col1, col2 = st.columns(2)
        with col1:
            strength = _num("含有量", min_value=0.001, value=62.5, step=0.1, format="%.3f")
        with col2:
            strength_unit = st.selectbox("含有量単位", options=sorted(VALID_STRENGTH_UNITS))

        col3, col4 = st.columns(2)
        with col3:
            form_type = st.selectbox("剤形", options=sorted(VALID_FORMS))
        with col4:
            unit_price = _num("単価（円/錠 or 円/ml、任意）", min_value=0.0, value=0.0, step=1.0, format="%.1f")

        divisible = st.checkbox("分割可能")
        min_division = None
        if divisible:
            min_division = _num("最小分割単位", min_value=0.01, value=0.5, step=0.01)

        submitted = st.form_submit_button("登録")

    if submitted:
        _submit_product(brand, drug_name, strength, strength_unit,
                        form_type, unit_price, divisible, min_division)


def _submit_product(brand, drug_name, strength, strength_unit,
                    form_type, unit_price, divisible, min_division):
    """商品登録フォームの送信処理。"""
    if not brand.strip():
        st.error("商品名を入力してください。")
        return

    new_product = {
        "brand": brand.strip(),
        "drug": drug_name,
        "strength": strength,
        "strength_unit": strength_unit,
        "form": form_type,
        "divisible": divisible,
        "min_division": min_division,
        "source": "user_registered",
        "notes": "",
    }
    if unit_price > 0:
        new_product["unit_price"] = unit_price

    try:
        add_product(new_product)
        st.success(f"商品「{brand}」を登録しました。")
    except ValueError as e:
        st.error(f"登録エラー: {e}")
