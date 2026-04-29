# Optimizer Specification

## 概要
数理最適化を実行し、最適な入荷スケジュールを計算する。

---

## 数学モデル

### 集合

- **商品の集合**: $P = \{p_1, p_2, \ldots\}$
- **日付の集合**: $D = \{d_1, d_2, \ldots\}$

### 意思決定変数

| 変数 | 定義 | コード (`optimizer.py`) |
|------|------|------|
| $x_{p,d}^{(s)}$ | 商品 $p$、日付 $d$ の小口（ケース）入荷数 | `x_small[p][d]` |
| $x_{p,d}^{(l)}$ | 商品 $p$、日付 $d$ の大口（トラック）入荷数 | `x_large[p][d]` |
| $n_d$ | 日付 $d$ のトラック台数（整数） | `n_trucks[d]` |
| $I_{p,d}$ | 商品 $p$、日付 $d$ の在庫 | `I[p][d]` |

### 入力データ

| パラメータ | 定義 | Excelソース |
|-----------|------|--------|
| $\bar{x}_{p,d}$ | ベース入荷予定数 | 時系列データ: 入荷予定 |
| $s_{p,d}$ | 出荷予測 | 時系列データ: 出荷予測 |
| $I_{p,0}$ | 前日末在庫 | 前日末在庫: 前日末在庫 |
| $S_{p,d}^{cum}$ | 出荷可能数累計 | 時系列データ: 出荷可能数累計 |

### 定数

| 定数 | 定義 | Excelソース |
|------|------|--------|
| $h_p$ | 1ケース1日当たり在庫保管コスト | 商品マスタ: 在庫コスト |
| $c_p^s$ | ケース配送単価 | 商品マスタ: 配送費_ケース |
| $C^l$ | トラック1台当たり配送費 | パラメータ: 配送費_車両 |
| $K_p$ | 満車ケース数 | 商品マスタ: CS/車両 |

### 目的関数

**最小化**: 総配送コスト + 総在庫保管コスト

$$\text{minimize} \quad \sum_{p,d} c_p^s \cdot x_{p,d}^{(s)} + \sum_{d} C^l \cdot n_d + \sum_{p,d} h_p \cdot I_{p,d}$$

### 制約条件

**1. 在庫推移**

$$I_{p,1} = I_{p,0} + x_{p,1}^{(s)} + x_{p,1}^{(l)} - s_{p,1}$$
$$I_{p,d} = I_{p,d-1} + x_{p,d}^{(s)} + x_{p,d}^{(l)} - s_{p,d} \quad (d > 1)$$

**2. トラック容量（混載対応）**

$$\sum_{p} \frac{x_{p,d}^{(l)}}{K_p} \le n_d \quad (d \in D)$$

**3. 累積入荷数 ≥ 累積ベース入荷予定（前倒しのみ可能）**

$$\sum_{\tau=1}^{d} (x_{p,\tau}^{(s)} + x_{p,\tau}^{(l)}) \ge \sum_{\tau=1}^{d} \bar{x}_{p,\tau} \quad (p \in P, d \in D)$$

**4. 累積入荷数 ≤ 出荷可能数累計**

$$\sum_{\tau=1}^{d} (x_{p,\tau}^{(s)} + x_{p,\tau}^{(l)}) \le S_{p,d}^{cum} \quad (p \in P, d \in D)$$

### 未実装の制約

- 今回発注の納品日以前の入荷禁止（$t_p$ パラメータ）

---

## 内部ヘルパー関数

`optimize()` と `calculate_baseline()` の両方から呼び出される共通処理を、`optimizer.py` 内のプライベート関数として定義する。

---

### `_prepare_inputs()` — 入力成型

**関数**: `_prepare_inputs(product_master_df, parameters_df, time_series_df, inventory_init_df) -> dict`

**役割**: 4つの DataFrame を、最適化・ベースライン計算で使いやすい集合・辞書に変換する。

**出力**: dict
```python
{
    "products_list": list,           # ソート済み商品コードリスト
    "days_list": list,               # ソート済み日付リスト
    "holding_cost": dict,            # {商品コード: h_p}
    "cost_per_case": dict,           # {商品コード: c_p^s}
    "cost_per_truck": float,         # C^l
    "max_cases_per_truck": dict,     # {商品コード: K_p}
    "x_bar": dict,                   # {(商品コード, 日付): ベース入荷予定}
    "shipping_forecast": dict,       # {(商品コード, 日付): 出荷予測}
    "inventory_init": dict,          # {商品コード: 前日末在庫}
    "cumulative_shippable_qty": dict, # {(商品コード, 日付): 出荷可能数累計}
}
```

**実装ファイル**: `optimizer.py:_prepare_inputs()`

---

### `_build_result()` — 出力成型

**関数**: `_build_result(products_list, days_list, x_small_values, x_large_values, n_trucks_values, inventory_values) -> tuple[DataFrame, DataFrame]`

**役割**: 数値辞書（PuLP変数の `.value()` 取得後、またはベースライン計算後）を `decision_variables_df` と `trucks_df` に変換する。

**入力**:
- `x_small_values`: `{(商品コード, 日付): float}`
- `x_large_values`: `{(商品コード, 日付): float}`
- `n_trucks_values`: `{日付: float}`
- `inventory_values`: `{(商品コード, 日付): float}`

**出力**: `(decision_variables_df, trucks_df)`

**decision_variables_df** スキーマ:
- 日付 (datetime)
- 商品コード (str)
- 小口入荷数 (float)
- 大口入荷数 (float)
- 入荷数合計 (float)
- 在庫 (float)

**trucks_df** スキーマ:
- 日付 (datetime)
- トラック台数 (int)

**実装ファイル**: `optimizer.py:_build_result()`

---

## 要件 O-1: 最適化関数の実装

**関数**: `optimize(product_master_df, parameters_df, time_series_df, inventory_init_df) -> dict`

**入力**:
- `product_master_df`: 商品マスタ DataFrame
  - カラム: 商品コード、在庫コスト、配送費_ケース、CS/車両
- `parameters_df`: パラメータ DataFrame
  - カラム: 項目、数量
- `time_series_df`: 時系列データ DataFrame
  - カラム: 商品コード、日付、入荷予定、出荷予測、出荷可能数累計
- `inventory_init_df`: 前日末在庫 DataFrame
  - カラム: 商品コード、前日末在庫

**処理フロー**:
1. `_prepare_inputs()` で入力を成型
2. PuLP でモデル構築・求解
3. `_build_result()` で出力を成型

**出力**: dict
```python
{
    "status": "Optimal" | "Not Solved" | ...,
    "total_cost": float | None,
    "decision_variables": DataFrame | None,
    "trucks": DataFrame | None,
}
```

**実装ファイル**: `optimizer.py:optimize()`

**テスト**: `tests/test_optimizer.py::test_O1_*`

---

## 要件 O-2: Excel ローダー

**関数**: `load_excel(excel_path: str) -> dict[str, pd.DataFrame]`

**入力**: Excel ファイルパス（4シート必須）
- シート名: 商品マスタ、パラメータ、時系列データ、前日末在庫

**出力**: dict
```python
{
    "product_master": DataFrame,
    "parameters": DataFrame,
    "time_series": DataFrame,
    "inventory_init": DataFrame,
}
```

**実装ファイル**: `optimizer.py:load_excel()`

**テスト**: `tests/test_optimizer.py::test_O2_*`

---

## 要件 O-3: 制約条件の正確性

### O-3-1: 在庫推移制約
- 初日: $I_{p,1} = I_{p,0} + x_{p,1} - s_{p,1}$
- 2日目以降: $I_{p,d} = I_{p,d-1} + x_{p,d} - s_{p,d}$
- すべての在庫は非負

**テスト**: `tests/test_optimizer.py::test_O3_1_inventory_transition()`

### O-3-2: トラック容量制約
- $\sum_p (x_p^{(l)} / K_p) \le n_d$

**テスト**: `tests/test_optimizer.py::test_O3_2_truck_capacity()`

### O-3-3: 累積入荷数制約
- $\sum_{\tau=1}^{d} x_{p,\tau} \ge \sum_{\tau=1}^{d} \bar{x}_{p,\tau}$ （前倒しのみ可能）
- $\sum_{\tau=1}^{d} x_{p,\tau} \le S_{p,d}^{cum}$ （出荷可能数限界）

**テスト**: `tests/test_optimizer.py::test_O3_3_cumulative_constraints()`

---

## 要件 O-4: エラーハンドリング

### O-4-1: 最適解が見つからない場合
- `status` に "Not Solved" など適切なステータスを返す
- `total_cost`, `decision_variables`, `trucks` は None

**テスト**: `tests/test_optimizer.py::test_O4_1_no_solution()`

### O-4-2: 不正な入力
- シート名不足、カラム不足などで例外発生
- エラーメッセージは明確

**テスト**: `tests/test_optimizer.py::test_O4_2_invalid_input()`

---

## 要件 O-5: ベースライン計算関数

**目的**: 最適化を行わず、入力データの入荷予定どおりに入荷した場合の在庫推移とコストを計算する。

**関数**: `calculate_baseline(product_master_df, parameters_df, time_series_df, inventory_init_df) -> dict`

**入力**: `optimize()` と同じ

**処理フロー**:
1. `_prepare_inputs()` で入力を成型
2. 入荷数・在庫を直接計算（PuLP不使用）
3. `_build_result()` で出力を成型

**計算ロジック**:
- `x_small[(p, d)]` = 入荷予定（`x_bar[(p, d)]`）
- `x_large[(p, d)]` = 0（大口入荷なし）
- `n_trucks[d]` = 0（トラックなし）
- 在庫推移: $I_{p,d} = I_{p,d-1} + x_{small,p,d} - s_{p,d}$（在庫が負になる場合も計算上はそのまま）
- `total_cost` = Σ 配送費_ケース × x_small + Σ 在庫コスト × 在庫

**出力**: `optimize()` と同じ dict 構造
```python
{
    "status": "Baseline",
    "total_cost": float,
    "decision_variables": DataFrame,  # optimize() と同じスキーマ
    "trucks": DataFrame,              # トラック台数 = 0 for all dates
}
```

**実装ファイル**: `optimizer.py:calculate_baseline()`

**テスト**: `tests/test_optimizer.py::TestO5_*`

---

## 実装制約

- ソルバー: CBC（PuLP via PULP_CBC_CMD）
- ログ出力: デフォルトは msg=0（無音）
