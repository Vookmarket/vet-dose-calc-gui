# vet-dose-calc-gui -- 獣医薬用量計算GUIツール

Streamlitベースの薬用量計算GUIアプリケーション。
CLI版（[vet-dose-calc](https://github.com/Vookmarket/vet-dose-calc)）のコアロジックをそのまま活用し、ブラウザで操作できるGUI版として再構成しました。

> **本ツールは試作品（プロトタイプ）です。**
> 実務で使用する場合は、出力内容を必ず専門家が確認してください。
> 不具合・改善提案は GitHub Issues へお寄せください。

## 機能

### 1. 用量計算（calc）
- 動物種（犬・猫）、体重、薬剤名を選択して用量を即時計算
- 登録済み商品ごとの投与量（錠数/ml数）を自動算出
- NTI薬（治療域が狭い薬剤）や猫禁忌薬の警告を視覚的に表示

### 2. 処方計算
- 投与日数・投与回数を入力して処方の総量を算出
- 商品に単価が登録されている場合、処方費用を自動計算
- 1回量・1日量・総量を見やすく表示

### 3. 薬剤提案（suggest）
- 症状キーワードからGemini API（Search Grounding）で薬剤候補を検索
- 候補ごとに用量・根拠URL・信頼度を表示
- 提案結果をワンクリックでDBに登録

### 4. マスタ管理（manage）
- 薬剤・商品の一覧表示、新規追加
- 商品の単価（円/錠、円/ml）をテーブル上で直接編集
- YAMLテンプレートからの一括インポート

## 動作環境

- Python 3.10+
- Streamlit 1.x
- ブラウザ（localhost:8501でアクセス）
- suggest機能使用時: Gemini APIキー（環境変数 `GEMINI_API_KEY`）

## インストール

```bash
# リポジトリをクローン
git clone https://github.com/Vookmarket/vet-dose-calc-gui.git
cd vet-dose-calc-gui

# CLI版（vet-dose-calc）も同じディレクトリに配置
# vet-dose-calc-gui/ と vet-dose-calc/ が同じ親ディレクトリにある前提
git clone https://github.com/Vookmarket/vet-dose-calc.git ../vet-dose-calc

# 依存パッケージをインストール
pip install streamlit PyYAML
```

## 使い方

```bash
# アプリケーション起動
streamlit run vet_dose_calc_gui/app.py
```

ブラウザが自動で開きます。開かない場合は `http://localhost:8501` にアクセスしてください。

### 用量計算の例

1. サイドバーで「用量計算」を選択
2. 動物種: 犬、体重: 5.0 kg、薬剤名: アモキシシリン/クラブラン酸 を入力
3. 「計算」ボタンをクリック
4. 結果: 一般感染症 62.5-125 mg / クラバモックス小型犬用 1錠

### 処方計算の例

1. 用量計算の結果表示後、「処方計算」セクションが表示される
2. 投与日数: 7日、投与回数/日: 2回（BID）
3. 結果: 総量 14錠、処方費用 700円（@50円/錠の場合）

## プロジェクト構成

```
vet_dose_calc_gui/
  __init__.py           # パッケージ初期化（__version__）
  app.py                # Streamlitエントリポイント
  prescription_calc.py  # 処方計算ロジック（pure Python）
  gui_formatter.py      # データ→GUI表示用変換
  pages/
    calc_page.py        # 用量計算画面
    suggest_page.py     # 薬剤提案画面
    manage_page.py      # マスタ管理画面
data/
  gui_config.yaml       # GUI固有設定
tests/
  test_prescription_calc.py  # 処方計算テスト（7ケース）
  test_gui_formatter.py      # フォーマッターテスト（7ケース）
```

## VT-004（CLI版）との関係

- コアロジック（用量計算、薬剤検索、商品管理、提案エンジン）はVT-004をそのまま再利用
- データファイル（drugs.yaml, products.yaml）はVT-004と共用
- GUIで追加した `unit_price`（単価）はVT-004のCLI版では無視される（後方互換性あり）

## 制約

- ローカル実行前提（Streamlit Cloudデプロイには永続化対策が別途必要）
- suggest機能にはGemini APIキーが必要
- VT-004が同じマシンの同階層に存在する前提
- 複数ユーザーの同時アクセスは想定外

## 情報源

- **Streamlit公式ドキュメント** -- Streamlit APIリファレンス
  https://docs.streamlit.io/
- **vet-dose-calc (VT-004)** -- CLI版リポジトリ（コアロジックの詳細）
  https://github.com/Vookmarket/vet-dose-calc

## 免責事項

このツールは参考補助を目的としており、獣医師による診断の代替ではありません。
臨床判断は必ず獣医師が行ってください。
このツールの出力にはAIによる生成が含まれます（suggest機能）。
