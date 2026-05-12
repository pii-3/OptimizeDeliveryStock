import pytest
import pandas as pd
from optimizer import load_excel


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
