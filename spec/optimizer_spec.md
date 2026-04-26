# Optimizer Specification

## 概要
数理最適化を実行し、最適な入荷スケジュールを計算する。

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

**出力**: dict
```python
{
    "status": "Optimal" | "Not Solved" | ...,
    "total_cost": float | None,
    "decision_variables": DataFrame | None,
    "trucks": DataFrame | None,
}
```

**decision_variables** DataFrame スキーマ:
- 日付 (datetime)
- 商品コード (str)
- 小口入荷数 (float)
- 大口入荷数 (float)
- 入荷数合計 (float)
- 在庫 (float)

**trucks** DataFrame スキーマ:
- 日付 (datetime)
- トラック台数 (int)

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

## 実装制約

- ソルバー: CBC（PuLP via PULP_CBC_CMD）
- ログ出力: デフォルトは msg=0（無音）
