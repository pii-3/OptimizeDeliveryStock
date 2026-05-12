import pytest
import pandas as pd
from optimizer import load_excel, _prepare_inputs


# ── O-2: Excel ローダー ────────────────────────────────────────────


def test_O2_1_returns_four_dataframes(sample_excel):
    result = load_excel(sample_excel)

    assert isinstance(result, dict)
    assert set(result.keys()) == {"product_master", "parameters", "time_series", "inventory_init"}
    for df in result.values():
        assert isinstance(df, pd.DataFrame)


def test_O2_2_missing_sheet_raises_error(tmp_path):
    path = tmp_path / "missing_sheet.xlsx"
    with pd.ExcelWriter(path) as writer:
        pd.DataFrame({"商品コード": ["A"], "在庫コスト": [1.0], "配送費_ケース": [100.0], "CS/車両": [50]}).to_excel(writer, sheet_name="商品マスタ", index=False)
        pd.DataFrame({"項目": ["配送費_車両"], "数量": [30000]}).to_excel(writer, sheet_name="パラメータ", index=False)
        pd.DataFrame({"商品コード": ["A"], "日付": [pd.Timestamp("2024-01-01")], "入荷予定": [10], "出荷予測": [8], "出荷可能数累計": [10]}).to_excel(writer, sheet_name="時系列データ", index=False)
        # 「前日末在庫」シートを意図的に省略

    with pytest.raises(ValueError, match="前日末在庫"):
        load_excel(path)


def test_O2_3_file_not_found_raises_error(tmp_path):
    path = tmp_path / "no_such_file.xlsx"

    with pytest.raises(FileNotFoundError):
        load_excel(path)


# ── _prepare_inputs ────────────────────────────────────────────────


def test_PI_1_products_and_days_are_sorted(sample_dfs):
    result = _prepare_inputs(*sample_dfs)

    assert result["products_list"] == ["A", "B"]
    assert result["days_list"] == [pd.Timestamp("2024-01-01"), pd.Timestamp("2024-01-02")]


def test_PI_2_costs_extracted_correctly(sample_dfs):
    result = _prepare_inputs(*sample_dfs)

    assert result["holding_cost"] == {"A": 1.0, "B": 2.0}
    assert result["cost_per_case"] == {"A": 100.0, "B": 200.0}
    assert result["cost_per_truck"] == 30000
    assert result["max_cases_per_truck"] == {"A": 50, "B": 40}


def test_PI_3_time_series_keyed_by_product_date(sample_dfs):
    result = _prepare_inputs(*sample_dfs)

    assert result["x_bar"][("A", pd.Timestamp("2024-01-01"))] == 10
    assert result["shipping_forecast"][("B", pd.Timestamp("2024-01-02"))] == 2
    assert result["cumulative_shippable_qty"][("A", pd.Timestamp("2024-01-02"))] == 15


def test_PI_4_inventory_init_keyed_by_product(sample_dfs):
    result = _prepare_inputs(*sample_dfs)

    assert result["inventory_init"] == {"A": 5, "B": 3}


def test_PI_5_missing_column_raises_error(sample_dfs):
    product_master, parameters, time_series, inventory_init = sample_dfs
    bad_product_master = product_master.drop(columns=["在庫コスト"])

    with pytest.raises(ValueError, match="在庫コスト"):
        _prepare_inputs(bad_product_master, parameters, time_series, inventory_init)
