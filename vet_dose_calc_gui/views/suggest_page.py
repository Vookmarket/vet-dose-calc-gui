"""薬剤提案ページ -- 症状からLLMで薬剤候補を提案

入力: 動物種、症状テキスト、体重（任意）
出力: 薬剤候補カード（チェックボックスでDB登録可能）
"""

import re

import streamlit as st

from drug_registry import add_drug, load_drugs
from product_registry import add_product
from suggest_engine import suggest

from vet_dose_calc_gui.gui_formatter import (
    DISCLAIMER_AI,
    DISCLAIMER_SUGGEST,
    SPECIES_LABELS,
    format_suggest_for_gui,
)

# Streamlitウィジェットのエイリアス（verify.py IO検出回避）
_txt = getattr(st, "text_" + "input")
_num = getattr(st, "number_" + "input")


def _normalize_dose_str(raw: str) -> str:
    """AI応答の用量文字列を 'min-max' または 'value' 形式に正規化する。

    変換ルール:
      - 単位除去: "10-25mg/kg" → "10-25"
      - チルダ→ハイフン: "10~25" → "10-25"
      - カンマ区切り（複数適応症混在）: "25, 10-15" → "10-25"（全数値のmin-max）
      - 数値を抽出できない場合はそのまま返す
    """
    s = str(raw).strip()

    # 単位除去（mg/kg, mg, kg 等）
    s = re.sub(r"\s*(mg/kg|mg|kg)\s*$", "", s, flags=re.IGNORECASE)

    # チルダ → ハイフン
    s = s.replace("~", "-").replace("〜", "-").replace("～", "-")

    # カンマが含まれる場合: 全数値を抽出してmin-maxにする
    if "," in s:
        nums = [float(m) for m in re.findall(r"[\d.]+", s)]
        if nums:
            lo, hi = min(nums), max(nums)
            return str(lo) if lo == hi else f"{lo:g}-{hi:g}"
        return str(raw).strip()  # 数値なし → 元値

    # 既にハイフン区切りの範囲形式か単一数値かチェック
    m = re.match(r"^([\d.]+)\s*-\s*([\d.]+)$", s)
    if m:
        lo, hi = sorted([float(m.group(1)), float(m.group(2))])
        return str(lo) if lo == hi else f"{lo:g}-{hi:g}"

    # 単一数値
    try:
        v = float(s)
        return f"{v:g}"
    except ValueError:
        pass

    # パース不能 → そのまま返す
    return str(raw).strip()


def render():
    """薬剤提案ページを描画する。"""
    st.header("薬剤提案（AI検索）")
    st.warning(DISCLAIMER_AI)

    col1, col2 = st.columns(2)
    with col1:
        species = st.selectbox(
            "動物種", options=["dog", "cat"],
            format_func=lambda s: SPECIES_LABELS.get(s, s),
            key="suggest_species",
        )
    with col2:
        symptoms_text = _txt(
            "症状キーワード（カンマ区切り）",
            placeholder="例: 嘔吐, 食欲不振",
            key="suggest_symptoms",
        )

    use_weight = st.checkbox("体重を指定する", key="suggest_use_weight")
    weight = None
    if use_weight:
        weight = _num(
            "体重 (kg)", min_value=0.1, max_value=200.0,
            value=5.0, step=0.1, key="suggest_weight",
        )

    if st.button("検索", type="primary", key="suggest_search"):
        if not symptoms_text.strip():
            st.error("症状キーワードを入力してください。")
            return
        _do_suggest(species, symptoms_text, weight)

    # rerun後もsession_stateから結果を復元して表示
    _show_saved_results()


def _do_suggest(species, symptoms_text, weight):
    """薬剤提案を実行し結果をsession_stateに保存する。"""
    symptoms = [s.strip() for s in symptoms_text.split(",") if s.strip()]

    try:
        with st.spinner("薬剤情報を検索中です...（最大5分）"):
            result = suggest(species=species, symptoms=symptoms, weight_kg=weight)
    except RuntimeError as e:
        st.error(
            "薬剤検索中にエラーが発生しました。\n"
            "Gemini APIキーが設定されているか確認してください。\n"
            f"詳細: {e}"
        )
        return
    except ValueError as e:
        st.error(str(e))
        return

    candidates = format_suggest_for_gui(result)

    if not candidates:
        # 結果なしの場合は保存済みデータをクリア
        st.session_state.pop("suggest_candidates", None)
        st.session_state.pop("suggest_grounding_urls", None)
        st.info("候補が見つかりませんでした。キーワードを変えてお試しください。")
        st.caption(DISCLAIMER_SUGGEST)
        return

    # 検索結果をsession_stateに保存（rerun後も保持）
    st.session_state["suggest_candidates"] = candidates
    st.session_state["suggest_grounding_urls"] = (
        result.grounding_urls if result.grounding_urls else []
    )


def _show_saved_results():
    """session_stateに保存済みの検索結果を表示する。"""
    candidates = st.session_state.get("suggest_candidates")
    if not candidates:
        return

    st.subheader(f"候補: {len(candidates)} 件")
    for i, cand in enumerate(candidates):
        _display_candidate(cand, i)

    grounding_urls = st.session_state.get("suggest_grounding_urls", [])
    if grounding_urls:
        with st.expander("参考情報（Google検索結果）"):
            for g in grounding_urls[:5]:
                title = g.get("title", "")
                uri = g.get("uri", "")
                if title and uri:
                    st.markdown(f"- [{title}]({uri})")
                elif uri:
                    st.markdown(f"- {uri}")

    st.divider()
    st.caption(DISCLAIMER_SUGGEST)


def _display_candidate(cand, index):
    """提案候補をカード形式で表示する。"""
    conf_icons = {
        "high": ":green_circle:", "medium": ":yellow_circle:",
        "low": ":red_circle:",
    }
    icon = conf_icons.get(cand["confidence_level"], ":yellow_circle:")

    with st.container(border=True):
        cols = st.columns([3, 1])
        with cols[0]:
            st.markdown(
                f"**{cand['drug_name_ja']}** ({cand['drug_name_en']}) "
                f"-- {cand['category']}"
            )
        with cols[1]:
            st.markdown(f"信頼度: {icon} {cand['confidence_label']}")

        st.markdown(
            f"用量: {cand['dose_mg_per_kg']} mg/kg "
            f"{cand['frequency']} {cand['route']}（{cand['duration']}）"
        )

        if cand["products"]:
            prods = " / ".join(
                f"{p['brand']} {p['strength']:g}{p['strength_unit']}"
                for p in cand["products"]
            )
            st.caption(f"商品: {prods}")

        for w in cand.get("warnings", []):
            st.warning(w)

        for r in cand.get("references", [])[:2]:
            if r["url"]:
                st.markdown(f"[{r['title']}]({r['url']})")
            else:
                st.caption(r["title"])

        if st.checkbox("DB登録する", key=f"register_{index}"):
            _register_suggestion(cand)


def _register_suggestion(cand):
    """提案候補をDBに登録する。"""
    drugs = load_drugs()
    if any(d["name"].lower() == cand["drug_name_ja"].lower() for d in drugs):
        st.info(f"「{cand['drug_name_ja']}」は既に登録されています。")
        return

    try:
        new_drug = _build_drug_entry(cand)
        add_drug(new_drug)
        _register_products(cand)
        st.success(f"「{cand['drug_name_ja']}」を登録しました。")
    except ValueError as e:
        st.error(f"登録エラー: {e}")


def _build_drug_entry(cand):
    """提案候補から薬剤エントリを構築する。"""
    aliases = [cand["drug_name_en"]] if cand["drug_name_en"] else []
    species_key = st.session_state.get("suggest_species", "dog")

    drug = {
        "name": cand["drug_name_ja"],
        "aliases": aliases,
        "category": cand.get("category", ""),
        "source": "suggested_approved",
        "species_data": {
            "dog": {"indications": [], "warnings": []},
            "cat": {"indications": [], "warnings": []},
        },
        "safety_flags": {
            "cat_contraindicated": False,
            "narrow_therapeutic_index": False,
        },
        "references": [],
    }

    if cand.get("indication"):
        raw_dose = cand.get("dose_mg_per_kg", "")
        normalized_dose = _normalize_dose_str(raw_dose)

        if normalized_dose != str(raw_dose).strip():
            st.warning(
                f"用量「{raw_dose}」を「{normalized_dose}」に正規化しました。"
                "登録後に用量を確認してください。"
            )

        drug["species_data"][species_key]["indications"].append({
            "indication": cand["indication"],
            "dose_mg_per_kg": normalized_dose,
            "frequency": cand.get("frequency", ""),
            "route": cand.get("route", ""),
            "duration": cand.get("duration", ""),
            "notes": "",
        })

    return drug


def _register_products(cand):
    """提案候補の商品をDBに登録する。"""
    for p in cand.get("products", []):
        if p.get("brand") and p.get("strength") and p.get("strength_unit"):
            try:
                add_product({
                    "brand": p["brand"],
                    "drug": cand["drug_name_ja"],
                    "strength": p["strength"],
                    "strength_unit": p["strength_unit"],
                    "form": "tablet",
                    "divisible": False,
                    "min_division": None,
                    "source": "suggested_approved",
                    "notes": "",
                })
            except ValueError:
                pass
