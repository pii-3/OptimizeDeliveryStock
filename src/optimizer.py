import pandas as pd
from pathlib import Path

SHEET_NAMES = {
    "商品マスタ": "product_master",
    "パラメータ": "parameters",
    "時系列データ": "time_series",
    "前日末在庫": "inventory_init",
}


def load_excel(excel_path):
    with pd.ExcelFile(Path(excel_path)) as xlsx:
        for sheet_name in SHEET_NAMES:
            if sheet_name not in xlsx.sheet_names:
                raise ValueError(f"必須シートがありません: {sheet_name}")
        return {key: xlsx.parse(sheet) for sheet, key in SHEET_NAMES.items()}
