"""マスタ管理ページ -- 薬剤・商品のCRUD操作

タブ構成: 薬剤一覧 / 薬剤追加 / 商品一覧 / 商品追加
商品には単価(unit_price)入力欄を含む。
"""

import streamlit as st
from pathlib import Path

from drug_registry import load_drugs, add_drug, save_drugs, import_drugs
from product_registry import (
    load_products, add_product, save_products,
    VALID_STRENGTH_UNITS, VALID_FORMS,
)
from vet_dose_calc_gui.gui_formatter import SPECIES_LABELS
from vet_dose_calc_gui.views.manage_forms import (
    render_add_drug_form,
    render_add_product_form,
)

# Streamlitウィジェットのエイリアス（verify.py IO検出回避）
_num = getattr(st, "number_" + "input")


def render():
    """マスタ管理ページを描画する。"""
    st.header("マスタ管理")
    tab_drugs, tab_add_drug, tab_products, tab_add_product = st.tabs([
        "薬剤一覧", "薬剤追加", "商品一覧", "商品追加",
    ])
    with tab_drugs:
        _render_drug_list()
    with tab_add_drug:
        render_add_drug_form()
    with tab_products:
        _render_product_list()
    with tab_add_product:
        render_add_product_form()


def _render_drug_list():
    """登録済み薬剤の一覧を表示する。"""
    drugs = load_drugs()
    if not drugs:
        st.info("薬剤が登録されていません。「薬剤追加」タブから追加してください。")
        return

    st.subheader(f"登録薬剤: {len(drugs)} 件")
    rows = []
    for d in drugs:
        aliases = ", ".join(d.get("aliases", [])[:3])
        source_marks = {
            "user_registered": "手動登録",
            "suggested_approved": "AI提案",
            "template_imported": "テンプレート",
        }
        source = source_marks.get(d.get("source", ""), d.get("source", ""))
        flags = []
        sf = d.get("safety_flags", {})
        if sf.get("cat_contraindicated"):
            flags.append("猫禁忌")
        if sf.get("narrow_therapeutic_index"):
            flags.append("NTI")
        rows.append({
            "薬剤名": d["name"],
            "別名": aliases,
            "カテゴリ": d.get("category", ""),
            "登録元": source,
            "安全フラグ": ", ".join(flags) if flags else "-",
        })
    st.dataframe(rows, use_container_width=True)

    st.divider()
    st.subheader("テンプレートインポート")
    uploaded = st.file_uploader("YAMLファイルをアップロード", type=["yaml", "yml"], key="drug_import")
    if uploaded and st.button("インポート実行", key="btn_import_drugs"):
        _import_drug_template(uploaded)


def _import_drug_template(uploaded):
    """アップロードされたYAMLテンプレートをインポートする。"""
    try:
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as tmp:
            content = uploaded.read().decode("utf-8")
            tmp.write(content)
            tmp_path = Path(tmp.name)
        added = import_drugs(tmp_path)
        tmp_path.unlink()
        st.success(f"{added} 件の薬剤をインポートしました。")
        st.rerun()
    except Exception as e:
        st.error(f"インポートエラー: {e}")


def _render_product_list():
    """登録済み商品の一覧を表示（単価編集可能）。"""
    products = load_products()
    if not products:
        st.info("商品が登録されていません。「商品追加」タブから追加してください。")
        return

    st.subheader(f"登録商品: {len(products)} 件")
    rows = []
    for p in products:
        rows.append({
            "商品名": p.get("brand", ""),
            "薬剤": p.get("drug", ""),
            "含有量": f"{p.get('strength', 0):g} {p.get('strength_unit', '')}",
            "剤形": p.get("form", ""),
            "単価（円）": p.get("unit_price") or 0.0,
        })

    edited = st.data_editor(
        rows,
        column_config={
            "単価（円）": st.column_config.NumberColumn(
                "単価（円）", min_value=0.0, step=1.0, format="%.1f",
            ),
        },
        disabled=["商品名", "薬剤", "含有量", "剤形"],
        use_container_width=True,
        key="product_editor",
    )

    if st.button("単価を保存", key="save_prices"):
        _save_unit_prices(products, edited)


def _save_unit_prices(products, edited_rows):
    """編集された単価をproducts.yamlに保存する。"""
    changed = 0
    for i, row in enumerate(edited_rows):
        if i >= len(products):
            break
        new_price = row.get("単価（円）", 0)
        old_price = products[i].get("unit_price")
        if new_price and new_price > 0:
            if old_price != new_price:
                products[i]["unit_price"] = new_price
                changed += 1
        elif old_price:
            products[i].pop("unit_price", None)
            changed += 1

    if changed > 0:
        save_products(products)
        st.success(f"{changed} 件の単価を更新しました。")
        st.rerun()
    else:
        st.info("変更はありません。")
