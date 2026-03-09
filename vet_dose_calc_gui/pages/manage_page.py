"""マスタ管理ページ -- 薬剤・商品のCRUD操作

タブ構成: 薬剤一覧 / 薬剤追加 / 商品一覧 / 商品追加
商品には単価(unit_price)入力欄を含む。
"""

import streamlit as st
import yaml
from pathlib import Path

from drug_registry import load_drugs, add_drug, save_drugs, import_drugs
from product_registry import (
    load_products,
    add_product,
    save_products,
    VALID_STRENGTH_UNITS,
    VALID_FORMS,
)

from vet_dose_calc_gui.gui_formatter import SPECIES_LABELS


def render():
    """マスタ管理ページを描画する。"""
    st.header("マスタ管理")

    tab_drugs, tab_add_drug, tab_products, tab_add_product = st.tabs([
        "薬剤一覧", "薬剤追加", "商品一覧", "商品追加",
    ])

    with tab_drugs:
        _render_drug_list()
    with tab_add_drug:
        _render_add_drug()
    with tab_products:
        _render_product_list()
    with tab_add_product:
        _render_add_product()


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

    # テンプレートインポート
    st.divider()
    st.subheader("テンプレートインポート")
    uploaded = st.file_uploader(
        "YAMLファイルをアップロード",
        type=["yaml", "yml"],
        key="drug_import",
    )
    if uploaded and st.button("インポート実行", key="btn_import_drugs"):
        _import_drug_template(uploaded)


def _import_drug_template(uploaded):
    """アップロードされたYAMLテンプレートをインポートする。"""
    try:
        import tempfile
        with tempfile.NamedTemporaryFile(
            suffix=".yaml", delete=False, mode="w"
        ) as tmp:
            content = uploaded.read().decode("utf-8")
            tmp.write(content)
            tmp_path = Path(tmp.name)

        added = import_drugs(tmp_path)
        tmp_path.unlink()
        st.success(f"{added} 件の薬剤をインポートしました。")
        st.rerun()
    except Exception as e:
        st.error(f"インポートエラー: {e}")


def _render_add_drug():
    """薬剤追加フォームを表示する。"""
    st.subheader("新規薬剤登録")

    with st.form("add_drug_form"):
        name = st.text_input("薬剤名（日本語）", placeholder="例: メロキシカム")
        aliases_text = st.text_input(
            "別名（カンマ区切り）",
            placeholder="例: meloxicam, メタカム",
        )
        category = st.selectbox("カテゴリ", options=[
            "antibiotics", "nsaid", "cardiovascular", "antiparasitic",
            "antiemetic", "analgesic", "sedative", "other",
        ])

        st.markdown("**適応症データ**")
        col1, col2 = st.columns(2)
        with col1:
            ind_species = st.selectbox(
                "動物種",
                options=["dog", "cat"],
                format_func=lambda s: SPECIES_LABELS.get(s, s),
                key="add_drug_species",
            )
        with col2:
            indication = st.text_input("適応症", value="一般", key="add_ind")

        col3, col4 = st.columns(2)
        with col3:
            dose_str = st.text_input(
                "用量 (mg/kg)",
                placeholder="例: 0.1-0.2",
                key="add_dose",
            )
        with col4:
            frequency = st.selectbox(
                "投与頻度",
                options=["SID", "BID", "TID", "QID", "EOD"],
                key="add_freq",
            )

        col5, col6 = st.columns(2)
        with col5:
            route = st.selectbox(
                "投与経路",
                options=["PO", "SC", "IM", "IV", "topical"],
                key="add_route",
            )
        with col6:
            duration = st.text_input(
                "投与期間",
                placeholder="例: 7-14日",
                key="add_duration",
            )

        is_nti = st.checkbox("NTI（治療域が狭い薬剤）")
        is_cat_contra = st.checkbox("猫禁忌")

        submitted = st.form_submit_button("登録")

    if submitted:
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
                "単価（円）",
                min_value=0.0,
                step=1.0,
                format="%.1f",
            ),
        },
        disabled=["商品名", "薬剤", "含有量", "剤形"],
        use_container_width=True,
        key="product_editor",
    )

    if st.button("単価を保存", key="save_prices"):
        _save_unit_prices(products, edited)


def _save_unit_prices(products: list[dict], edited_rows: list[dict]):
    """編集された単価をproducts.yamlに保存する。"""
    changed = 0
    for i, row in enumerate(edited_rows):
        if i < len(products):
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


def _render_add_product():
    """商品追加フォームを表示する。"""
    st.subheader("新規商品登録")

    drugs = load_drugs()
    drug_names = [d["name"] for d in drugs]

    if not drug_names:
        st.warning("先に薬剤を登録してください。")
        return

    with st.form("add_product_form"):
        brand = st.text_input("商品名", placeholder="例: クラバモックス小型犬用")
        drug_name = st.selectbox("紐づけ薬剤", options=drug_names)

        col1, col2 = st.columns(2)
        with col1:
            strength = st.number_input(
                "含有量",
                min_value=0.001,
                value=62.5,
                step=0.1,
                format="%.3f",
            )
        with col2:
            strength_unit = st.selectbox(
                "含有量単位",
                options=sorted(VALID_STRENGTH_UNITS),
            )

        col3, col4 = st.columns(2)
        with col3:
            form_type = st.selectbox("剤形", options=sorted(VALID_FORMS))
        with col4:
            unit_price = st.number_input(
                "単価（円/錠 or 円/ml、任意）",
                min_value=0.0,
                value=0.0,
                step=1.0,
                format="%.1f",
            )

        divisible = st.checkbox("分割可能")
        min_division = None
        if divisible:
            min_division = st.number_input(
                "最小分割単位",
                min_value=0.01,
                value=0.5,
                step=0.01,
            )

        submitted = st.form_submit_button("登録")

    if submitted:
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
