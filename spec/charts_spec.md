# Charts Specification

## 概要
最適化結果をグラフ化するための仕様書。matplotlib を使用。

---

## 要件 C-1: 全商品合計の在庫推移グラフ

**目的**: 全商品の在庫がどのように推移するかを可視化

**入力**:
- `decision_variables` DataFrame: 日付、商品コード、在庫カラム

**出力**:
- matplotlib Figure オブジェクト

**表示内容**:
- X軸: 日付（MM/DD 形式）
- Y軸: 在庫数（合計）
- グラフ: 折れ線グラフ、マーカー付き
- グリッド: ON

**実装ファイル**: `charts.py:plot_inventory_all()`

**テスト**: `tests/test_charts.py::test_C1_plot_inventory_all()`

---

## 要件 C-2: 商品ごとの在庫推移グラフ

**目的**: 各商品の在庫推移を個別に確認

**入力**:
- `decision_variables` DataFrame: 日付、商品コード、在庫カラム

**出力**:
- matplotlib Figure オブジェクト（複数サブプロット）

**表示内容**:
- 商品数分のサブプロット（縦方向に積み上げ）
- 各プロット:
  - X軸: 日付（MM/DD 形式、共有）
  - Y軸: 在庫数（商品ごと）
  - グラフ: 折れ線グラフ、マーカー付き
  - タイトル: 「商品コード 在庫推移」
  - グリッド: ON

**実装ファイル**: `charts.py:plot_inventory_by_product()`

**テスト**: `tests/test_charts.py::test_C2_plot_inventory_by_product()`

---

## 要件 C-3: 商品ごとの入荷数・在庫推移グラフ

**目的**: 入荷タイミングと在庫残高の関係を確認

**入力**:
- `decision_variables` DataFrame: 日付、商品コード、小口入荷数、大口入荷数、在庫カラム

**出力**:
- matplotlib Figure オブジェクト（複数サブプロット）

**表示内容**:
- 商品数分のサブプロット（縦方向に積み上げ）
- 各プロット:
  - 主軸Y: 入荷数（棒グラフ、積み上げ）
    - 小口入荷数: 色A
    - 大口入荷数: 色B（小口の上に積み上げ）
  - 副軸Y（右側）: 在庫（折れ線、赤色）
  - X軸: 日付（MM/DD 形式、共有）
  - タイトル: 「商品コード 入荷数・在庫推移」
  - グリッド: X軸のみ

**実装ファイル**: `charts.py:plot_order_and_inventory_by_product()`

**テスト**: `tests/test_charts.py::test_C3_plot_order_and_inventory_by_product()`

---

## 統合要件

### I-1: Streamlit への統合
- `app.py` で最適化結果取得後、以下を順に表示:
  1. C-1 グラフ
  2. C-2 グラフ
  3. C-3 グラフ

### I-2: 出力オプション
- 各グラフを個別に PNG ダウンロード可能（オプション）

---

## 技術的な制約

- **ライブラリ**: matplotlib のみ（plotly 不可）
- **フォント**: システムデフォルト
- **DPI**: 100
- **図サイズ**: 柔軟（Streamlit の幅に合わせる）
