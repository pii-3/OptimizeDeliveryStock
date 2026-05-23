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
| $u_p$ | 発注単位（入荷数合計はこの整数倍のみ許容） | 商品マスタ: 発注単位 |

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

**5. 発注単位制約（`optimize()` のみ）**

$$x_{p,d}^{(s)} = k_{p,d}^{(s)} \cdot u_p \quad (p \in P, d \in D, \; k_{p,d}^{(s)} \in \mathbb{Z}_{\ge 0})$$
$$x_{p,d}^{(l)} = k_{p,d}^{(l)} \cdot u_p \quad (p \in P, d \in D, \; k_{p,d}^{(l)} \in \mathbb{Z}_{\ge 0})$$

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
    "products_list": list,           # ソート済み商品コードリスト（時系列データに存在する商品のみ）
    "days_list": list,               # ソート済み日付リスト
    "holding_cost": dict,            # {商品コード: h_p}
    "cost_per_case": dict,           # {商品コード: c_p^s}
    "cost_per_truck": float,         # C^l
    "max_cases_per_truck": dict,     # {商品コード: K_p}
    "x_bar": dict,                   # {(商品コード, 日付): ベース入荷予定}（欠損は 0）
    "shipping_forecast": dict,       # {(商品コード, 日付): 出荷予測}（欠損は 0）
    "inventory_init": dict,          # {商品コード: 前日末在庫}
    "cumulative_shippable_qty": dict, # {(商品コード, 日付): 出荷可能数累計}
    "order_unit": dict,               # {商品コード: u_p}
}
```

> **注意**: `products_list` は商品マスタではなく時系列データに存在する商品コードから生成する。
> 商品マスタにあっても時系列データに存在しない商品は計算対象外となる。

**実装ファイル**: `optimizer.py:_prepare_inputs()`

---

### テスト要件（_prepare_inputs）

> `_prepare_inputs` はプライベート関数だが、`optimize` と `calculate_baseline` の両方から
> 呼ばれる中核処理なので直接テストする。カラム検証もここで行う（O-2 では行わない）。
>
> fixture は `tests/conftest.py` の `sample_dfs` を使う。
> 2商品（A・B）× 2日付で構成し、ソート検証のため入力は意図的に逆順にしてある。

#### test_PI_1_products_and_days_are_sorted

**目的**: 商品コードリストと日付リストがそれぞれ昇順にソートされていること。

**検証**:
- `result["products_list"] == ["A", "B"]`
- `result["days_list"] == [Timestamp("2024-01-01"), Timestamp("2024-01-02")]`

---

#### test_PI_2_costs_extracted_correctly

**目的**: コスト関連パラメータが正しく抽出・変換されていること。

**検証**:
- `result["holding_cost"] == {"A": 1.0, "B": 2.0}`
- `result["cost_per_case"] == {"A": 100.0, "B": 200.0}`
- `result["cost_per_truck"] == 30000`
- `result["max_cases_per_truck"] == {"A": 50, "B": 40}`
- `result["order_unit"] == {"A": 1, "B": 1}`

---

#### test_PI_3_time_series_keyed_by_product_date

**目的**: 時系列データが `(商品コード, 日付)` のタプルをキーとした dict に変換されていること。

**検証**:
- `result["x_bar"][("A", Timestamp("2024-01-01"))] == 10`
- `result["shipping_forecast"][("B", Timestamp("2024-01-02"))] == 2`
- `result["cumulative_shippable_qty"][("A", Timestamp("2024-01-02"))] == 15`

---

#### test_PI_4_inventory_init_keyed_by_product

**目的**: 初期在庫が商品コードをキーとした dict に変換されていること。

**検証**:
- `result["inventory_init"] == {"A": 5, "B": 3}`

---

#### test_PI_5_missing_column_raises_error

**目的**: カラム検証。必須カラムが欠けていると `ValueError` を送出すること。

**テストデータ**: `在庫コスト` カラムを除いた `product_master` を渡す。

**検証**:
- `ValueError` が送出される
- エラーメッセージに `"在庫コスト"` が含まれる

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
  - カラム: 商品コード、在庫コスト、配送費_ケース、CS/車両、発注単位
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
    "cost_breakdown": {          # コスト内訳（最適解なし時は None）
        "delivery_small": float, # 配送コスト（小口）= Σ c_p^s × x_small
        "delivery_large": float, # 配送コスト（大口）= Σ C^l × n_d
        "holding": float,        # 在庫コスト = Σ h_p × I
    } | None,
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

### テスト要件（O-2）

> `load_excel` の責務は「4シートを読んで dict に入れること」のみ。
> カラム名の検証は `_prepare_inputs` に任せる（最適化モデルが必要とするカラムは
> そこで変わりにくいため、検証の置き場として適切）。

#### fixture: `sample_excel` （conftest.py に定義）

テスト用の最小限 Excel ファイルを一時ディレクトリに作成して返す。

#### test_O2_1_returns_four_dataframes

**目的**: 正常系。4シートが正しいキーで読み込まれること。

**テストデータ**: `sample_excel` fixture

**検証**:
- 返り値の型が `dict` である
- キーが `{"product_master", "parameters", "time_series", "inventory_init"}` と一致する
- 各値が `pd.DataFrame` である

---

#### test_O2_2_missing_sheet_raises_error

**目的**: エラー系。必須シートが1つ欠けていたら例外を送出すること。

**テストデータ**: `前日末在庫` シートだけ含まない Excel ファイルを `tmp_path` に作成する。

**検証**:
- `load_excel()` を呼ぶと `ValueError`（またはサブクラス）が送出される
- エラーメッセージに欠けているシート名（`"前日末在庫"`）が含まれる

---

#### test_O2_3_file_not_found_raises_error

**目的**: エラー系。存在しないパスを渡したら `FileNotFoundError` が送出されること。

**テストデータ**: 存在しないパス（例: `tmp_path / "no_such_file.xlsx"`）

**検証**:
- `load_excel()` を呼ぶと `FileNotFoundError` が送出される

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
    "cost_breakdown": {
        "delivery_small": float,
        "delivery_large": float,  # ベースラインでは 0
        "holding": float,
    },
    "decision_variables": DataFrame,  # optimize() と同じスキーマ
    "trucks": DataFrame,              # トラック台数 = 0 for all dates
}
```

**実装ファイル**: `optimizer.py:calculate_baseline()`

**テスト**: `tests/test_optimizer.py::TestO5_*`

---

## 要件 O-6: 発注数固定の最適化関数

**目的**: 各（日付×商品）の入荷数合計を入荷予定（x_bar）に固定したまま、小口・大口の配送振り分けとトラック台数を最適化してコストを最小化する。前倒し・後ろ倒しなし。

**関数**: `optimize_fixed_order(product_master_df, parameters_df, time_series_df, inventory_init_df) -> dict`

**入力**: `optimize()` と同じ

**処理フロー**:
1. `_prepare_inputs()` で入力を成型
2. PuLP でモデル構築・求解
3. `_build_result()` で出力を成型

**数学モデル**:

意思決定変数: $x_{p,d}^{(s)}$、$x_{p,d}^{(l)}$、$n_d$（$I_{p,d}$ は x_bar から一意に決まるため変数不要）

目的関数:
$$\text{minimize} \quad \sum_{p,d} c_p^s \cdot x_{p,d}^{(s)} + \sum_{d} C^l \cdot n_d + \sum_{p,d} h_p \cdot I_{p,d}$$

制約条件:
1. **発注数固定**: $x_{p,d}^{(s)} + x_{p,d}^{(l)} = \bar{x}_{p,d} \quad (\forall p, d)$
2. **トラック容量**: $\sum_p \frac{x_{p,d}^{(l)}}{K_p} \le n_d \quad (\forall d)$
3. **在庫推移**: `optimize()` と同じ（非負制約なし — x_bar どおり入荷すると在庫が負になるケースも許容）

**出力**: `optimize()` と同じ dict 構造（`status` は "Optimal" または非最適ステータス）

**実装ファイル**: `optimizer.py:optimize_fixed_order()`

**テスト**: `tests/test_optimizer.py::TestO6_*`

---

## 要件 O-7: 発注単位制約（optimize のみ）

**目的**: 入荷数合計（小口＋大口）が商品ごとの発注単位 $u_p$ の整数倍に限定されることを保証する。

**対象関数**: `optimize()` のみ（`optimize_fixed_order` や `calculate_baseline` には適用しない）

**数学モデル追加**:
- 整数変数: $k_{p,d}^{(s)}, k_{p,d}^{(l)} \ge 0 \; (k \in \mathbb{Z})$
- 制約: $x_{p,d}^{(s)} = k_{p,d}^{(s)} \cdot u_p$、$x_{p,d}^{(l)} = k_{p,d}^{(l)} \cdot u_p \quad (\forall p, d)$

**fixture** `dfs_with_order_unit`:
- 商品 U、発注単位 = 5
- x_bar = 7、出荷予測 = 7、出荷可能数累計 = 10、前日末在庫 = 0
- トラック単価を非常に高く設定（小口のみ選択させる）

#### test_O7_1_order_quantity_is_multiple_of_unit

**目的**: 小口入荷数が発注単位の整数倍になること（トラック非常に高いので大口=0）。

**検証**:
- `result["status"] == "Optimal"`
- `入荷数合計 == 10.0`（x_bar=7 を満たす 発注単位 5 の最小倍数は 10）

**テスト**: `tests/test_optimizer.py::test_O7_1_order_quantity_is_multiple_of_unit`

---

**fixture** `dfs_with_order_unit_each`:
- 商品 V、発注単位 = 5、CS/車両 = 8（トラック積載上限 8 ケース）
- 配送費_ケース = 1、配送費_車両 = 3
- x_bar = 10、出荷予測 = 10、出荷可能数累計 = 10、前日末在庫 = 0
- 旧制約（合計 = 5k）では x_large=8, x_small=2 (cost=5) が最適
- 新制約（各変数 = 5k）では (0, 10) (cost=6) が最適

#### test_O7_2_each_variable_is_multiple_of_unit

**目的**: 小口・大口それぞれが発注単位の整数倍になること。

**検証**:
- `result["status"] == "Optimal"`
- `小口入荷数 % 5 == 0`
- `大口入荷数 % 5 == 0`
- `大口入荷数 == 10.0`（旧制約では 8 になっていた）

**テスト**: `tests/test_optimizer.py::test_O7_2_each_variable_is_multiple_of_unit`

---

## 実装制約

- ソルバー: CBC（PuLP via PULP_CBC_CMD）
- ログ出力: デフォルトは msg=0（無音）
