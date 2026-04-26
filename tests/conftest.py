import pytest
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt


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


@pytest.fixture(autouse=True)
def close_all_figures():
    """各テスト後に全ての figure をクローズ"""
    yield
    plt.close("all")
