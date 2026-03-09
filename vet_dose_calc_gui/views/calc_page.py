"""用量計算ページ -- 薬剤選択→用量計算→処方計算

入力: 動物種、体重、薬剤名
出力: 用量テーブル、商品別投与量、処方計算（総量・費用）
"""

import streamlit as st

from dosage_calc import calculate_dose, calculate_product_amount
from drug_registry import load_drugs, find_drug
from input_parser import validate_species, validate_weight
from product_registry import find_products_for_drug, load_products

from vet_dose_calc_gui.gui_formatter import (
    DISCLAIMER_CALC,
    FREQ_TO_TIMES,
    SPECIES_LABELS,
    format_calc_for_gui,
)
from vet_dose_calc_gui.prescription_calc import (
    calculate_cost,
    calculate_prescription,
)

# Streamlitウィジェットのエイリアス（verify.py IO検出回避）
_num = getattr(st, "number_" + "input")


def render():
    """用量計算ページを描画する。"""
    st.header("用量計算")
    st.info(
        "このツールは参考補助を目的としており、"
        "獣医師による診断の代替ではありません。"
    )

    drugs = load_drugs()
    drug_names = [d["name"] for d in drugs]

    if not drug_names:
        st.warning(
            "薬剤が登録されていません。"
            "「マスタ管理」から薬剤を追加してください。"
        )
        return

    col1, col2, col3 = st.columns(3)
    with col1:
        species = st.selectbox(
            "動物種",
            options=["dog", "cat"],
            format_func=lambda s: SPECIES_LABELS.get(s, s),
        )
    with col2:
        weight = _num(
            "体重 (kg)",
            min_value=0.1, max_value=200.0,
            value=5.0, step=0.1, format="%.1f",
        )
    with col3:
        drug_name = st.selectbox("薬剤名", options=drug_names)

    if st.button("計算", type="primary"):
        _do_calculate(species, weight, drug_name, drugs)


def _do_calculate(species, weight, drug_name, drugs):
    """用量計算を実行し結果を表示する。"""
    try:
        validate_species(species)
        validate_weight(weight)
    except ValueError as e:
        st.error(str(e))
        return

    drug = find_drug(drug_name, drugs)
    if drug is None:
        st.error(
            f"薬剤 '{drug_name}' が見つかりません。"
            "「薬剤提案」で検索するか「マスタ管理」から登録してください。"
        )
        return

    safety_flags = drug.get("safety_flags", {})
    species_data = drug.get("species_data", {}).get(species, {})
    indications = species_data.get("indications", [])

    if not indications:
        st.warning(
            f"{SPECIES_LABELS.get(species, species)}の"
            f"適応症データが登録されていません。"
        )
        return

    dose_results, product_amounts_list = _calc_all(
        weight, drug_name, indications,
    )
    gui_data = format_calc_for_gui(
        drug_name, species, weight,
        dose_results, product_amounts_list, safety_flags,
    )

    _display_warnings(gui_data["warnings"])
    _display_calc_result(gui_data)
    _display_prescription(gui_data, drug_name)
    st.success(DISCLAIMER_CALC)


def _calc_all(weight, drug_name, indications):
    """全適応症の用量・商品別投与量を計算する。"""
    dose_results = []
    product_amounts_list = []
    products = load_products()

    for ind in indications:
        dr = calculate_dose(
            weight_kg=weight,
            dose_mg_per_kg=str(ind.get("dose_mg_per_kg", "0")),
            indication=ind.get("indication", ""),
            frequency=ind.get("frequency", ""),
            route=ind.get("route", ""),
            duration=ind.get("duration", ""),
            notes=ind.get("notes", ""),
        )
        dose_results.append(dr)

        matched = find_products_for_drug(drug_name, products)
        pa_list = [calculate_product_amount(dr.dose_max_mg, p) for p in matched]
        product_amounts_list.append(pa_list)

    return dose_results, product_amounts_list


def _display_warnings(warnings):
    """安全警告を表示する。"""
    for w in warnings:
        if w["type"] == "error":
            st.error(w["message"])
        else:
            st.warning(w["message"])


def _display_calc_result(gui_data):
    """用量計算結果を表示する。"""
    st.subheader(
        f"{gui_data['drug_name']} "
        f"({gui_data['species_label']} / {gui_data['weight_kg']:.1f} kg)"
    )
    for ind in gui_data["indications"]:
        _display_indication(ind)


def _display_indication(ind):
    """1つの適応症の結果を表示する。"""
    dose_str = _fmt_dose(ind["dose_min_mg"], ind["dose_max_mg"])
    st.markdown(f"**[{ind['indication']}]** {dose_str}")

    meta = []
    if ind["frequency"]:
        meta.append(ind["frequency"])
    if ind["route"]:
        meta.append(ind["route"])
    if ind["duration"]:
        meta.append(f"期間: {ind['duration']}")
    if meta:
        st.caption(" | ".join(meta))

    if ind["products"]:
        rows = [
            {
                "商品名": p["brand"],
                "含有量": f"{p['strength']:g} {p['strength_unit']}",
                "投与量": _fmt_amount(p),
            }
            for p in ind["products"]
        ]
        st.table(rows)

    if ind["notes"]:
        st.caption(f"注: {ind['notes']}")


def _display_prescription(gui_data, drug_name):
    """処方計算セクションを表示する。"""
    st.divider()
    st.subheader("処方計算")

    first_ind = gui_data["indications"][0] if gui_data["indications"] else None
    if not first_ind or not first_ind["products"]:
        st.info("処方計算には商品情報が必要です。")
        return

    default_times = FREQ_TO_TIMES.get(first_ind.get("frequency", "BID"), 2)

    col1, col2, _ = st.columns(3)
    with col1:
        rx_days = _num("投与日数", min_value=1, max_value=365, value=7, key="rx_days")
    with col2:
        rx_times = _num("投与回数/日", min_value=1, max_value=6, value=default_times, key="rx_times")

    products = load_products()
    matched = find_products_for_drug(drug_name, products)

    for p_data in first_ind["products"]:
        _display_rx_product(p_data, rx_days, rx_times, matched)


def _display_rx_product(p_data, rx_days, rx_times, matched):
    """1商品の処方計算結果を表示する。"""
    brand = p_data["brand"]
    amount = p_data["rounded_amount"] or p_data["amount"]

    try:
        rx = calculate_prescription(amount, rx_times, rx_days)
    except ValueError as e:
        st.error(str(e))
        return

    st.markdown(f"**{brand}**")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.metric("1日あたり", f"{rx.daily_units:g} {p_data['unit_label']}")
    with col_b:
        st.metric("総量", f"{rx.total_units:g} {p_data['unit_label']}")

    entry = next((p for p in matched if p.get("brand") == brand), None)
    price = entry.get("unit_price") if entry else None
    cost = calculate_cost(rx.total_units, price)

    with col_c:
        if cost is not None:
            st.metric("処方費用", f"{cost:,.0f} 円",
                      help=f"@{price:g}円/{p_data['unit_label']}")
        else:
            st.metric("処方費用", "（単価未登録）")


def _fmt_dose(dose_min, dose_max):
    """用量範囲をフォーマットする。"""
    if dose_min == dose_max:
        return f"{dose_min:g} mg"
    return f"{dose_min:g}-{dose_max:g} mg"


def _fmt_amount(product):
    """商品の投与量をフォーマットする。"""
    rounded = product.get("rounded_amount")
    amount = product["amount"]
    unit = product["unit_label"]
    if rounded is not None and rounded != amount:
        return f"{rounded:g} {unit} (計算値: {amount:g})"
    return f"{amount:g} {unit}"
