import matplotlib
matplotlib.use('Agg')  # テスト実行時はヘッドレスバックエンドを使用（Tk 不要）

import pytest
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt


@pytest.fixture
def simple_input_data():
    """制約検証用シンプルデータ（1商品・3日間、手計算可能な数値）

    期待する最適解:
      x_small = 10 / 日（大口は使わない）
      在庫 = 0 / 日
      total_cost = 10 * 100 * 3 = 3000
    """
    dates = pd.date_range("2026-01-01", periods=3)
    return {
        "product_master": pd.DataFrame({
            "商品コード": ["P001"],
            "在庫コスト": [10],
            "配送費_ケース": [100],
            "CS/車両": [1000],  # 大口が割高になるよう大きな値
        }),
        "parameters": pd.DataFrame({
            "項目": ["配送費_車両"],
            "数量": [5000],
        }),
        "time_series": pd.DataFrame({
            "商品コード": ["P001"] * 3,
            "日付": dates,
            "入荷予定": [10, 10, 10],
            "出荷予測": [10, 10, 10],
            "出荷可能数累計": [30, 30, 30],
        }),
        "inventory_init": pd.DataFrame({
            "商品コード": ["P001"],
            "前日末在庫": [0],
        }),
    }


@pytest.fixture
def infeasible_input_data():
    """最適解なしケース（出荷可能数累計=5 < 累積入荷予定=10 で矛盾）"""
    dates = pd.date_range("2026-01-01", periods=2)
    return {
        "product_master": pd.DataFrame({
            "商品コード": ["P001"],
            "在庫コスト": [10],
            "配送費_ケース": [100],
            "CS/車両": [1000],
        }),
        "parameters": pd.DataFrame({
            "項目": ["配送費_車両"],
            "数量": [5000],
        }),
        "time_series": pd.DataFrame({
            "商品コード": ["P001"] * 2,
            "日付": dates,
            "入荷予定": [10, 10],        # 累積入荷予定: 10, 20
            "出荷予測": [10, 10],
            "出荷可能数累計": [5, 5],    # 上限5 < 下限10 → 矛盾
        }),
        "inventory_init": pd.DataFrame({
            "商品コード": ["P001"],
            "前日末在庫": [0],
        }),
    }


@pytest.fixture
def simple_result(simple_input_data):
    """simple_input_data の最適化結果（O-3 制約検証用）"""
    from optimizer import optimize
    return optimize(
        simple_input_data["product_master"],
        simple_input_data["parameters"],
        simple_input_data["time_series"],
        simple_input_data["inventory_init"],
    )


@pytest.fixture
def simple_baseline_result(simple_input_data):
    """simple_input_data のベースライン計算結果（O-5 用）"""
    from optimizer import calculate_baseline
    return calculate_baseline(
        simple_input_data["product_master"],
        simple_input_data["parameters"],
        simple_input_data["time_series"],
        simple_input_data["inventory_init"],
    )


@pytest.fixture
def sample_input_data():
    """サンプル入力データを読み込む"""
    excel_path = Path(__file__).parent.parent / "data" / "input" / "InputData.xlsx"
    dfs = pd.read_excel(excel_path, sheet_name=None)
    return {
        "product_master": dfs["商品マスタ"],
        "parameters": dfs["パラメータ"],
        "time_series": dfs["時系列データ"],
        "inventory_init": dfs["前日末在庫"],
    }


@pytest.fixture
def sample_decision_variables(sample_input_data):
    """サンプル最適化結果（decision_variables DataFrame）"""
    from optimizer import optimize
    result = optimize(
        sample_input_data["product_master"],
        sample_input_data["parameters"],
        sample_input_data["time_series"],
        sample_input_data["inventory_init"],
    )
    return result["decision_variables"]


@pytest.fixture
def sample_trucks(sample_input_data):
    """サンプル最適化結果（trucks DataFrame）"""
    from optimizer import optimize
    result = optimize(
        sample_input_data["product_master"],
        sample_input_data["parameters"],
        sample_input_data["time_series"],
        sample_input_data["inventory_init"],
    )
    return result["trucks"]


@pytest.fixture
def simple_fixed_order_result(simple_input_data):
    """simple_input_data の発注数固定最適化結果（O-6 用）"""
    from optimizer import optimize_fixed_order
    return optimize_fixed_order(
        simple_input_data["product_master"],
        simple_input_data["parameters"],
        simple_input_data["time_series"],
        simple_input_data["inventory_init"],
    )


@pytest.fixture(autouse=True)
def close_all_figures():
    """各テスト後に全ての figure をクローズ"""
    yield
    plt.close("all")
