import pytest
import pandas as pd


@pytest.fixture
def sample_dfs():
    # 商品・日付ともに逆順で用意 — ソート検証のため
    product_master = pd.DataFrame({
        "商品コード": ["B", "A"],
        "在庫コスト": [2.0, 1.0],
        "配送費_ケース": [200.0, 100.0],
        "CS/車両": [40, 50],
    })
    parameters = pd.DataFrame({
        "項目": ["配送費_車両"],
        "数量": [30000],
    })
    time_series = pd.DataFrame({
        "商品コード": ["A", "B", "A", "B"],
        "日付": [pd.Timestamp("2024-01-02"), pd.Timestamp("2024-01-02"),
                 pd.Timestamp("2024-01-01"), pd.Timestamp("2024-01-01")],
        "入荷予定": [5, 3, 10, 8],
        "出荷予測": [4, 2, 8, 6],
        "出荷可能数累計": [15, 11, 10, 8],
    })
    inventory_init = pd.DataFrame({
        "商品コード": ["B", "A"],
        "前日末在庫": [3, 5],
    })
    return product_master, parameters, time_series, inventory_init


@pytest.fixture
def sample_excel(tmp_path):
    path = tmp_path / "test_input.xlsx"
    with pd.ExcelWriter(path) as writer:
        pd.DataFrame({
            "商品コード": ["A"],
            "在庫コスト": [1.0],
            "配送費_ケース": [100.0],
            "CS/車両": [50],
        }).to_excel(writer, sheet_name="商品マスタ", index=False)

        pd.DataFrame({
            "項目": ["配送費_車両"],
            "数量": [30000],
        }).to_excel(writer, sheet_name="パラメータ", index=False)

        pd.DataFrame({
            "商品コード": ["A"],
            "日付": [pd.Timestamp("2024-01-01")],
            "入荷予定": [10],
            "出荷予測": [8],
            "出荷可能数累計": [10],
        }).to_excel(writer, sheet_name="時系列データ", index=False)

        pd.DataFrame({
            "商品コード": ["A"],
            "前日末在庫": [5],
        }).to_excel(writer, sheet_name="前日末在庫", index=False)
    return path
