import pandas as pd
from pathlib import Path

SHEET_NAMES = {
    "商品マスタ": "product_master",
    "パラメータ": "parameters",
    "時系列データ": "time_series",
    "前日末在庫": "inventory_init",
}


_REQUIRED_COLUMNS = {
    "product_master": ["商品コード", "在庫コスト", "配送費_ケース", "CS/車両"],
    "parameters": ["項目", "数量"],
    "time_series": ["商品コード", "日付", "入荷予定", "出荷予測", "出荷可能数累計"],
    "inventory_init": ["商品コード", "前日末在庫"],
}


def _prepare_inputs(product_master_df, parameters_df, time_series_df, inventory_init_df):
    dfs = {
        "product_master": product_master_df,
        "parameters": parameters_df,
        "time_series": time_series_df,
        "inventory_init": inventory_init_df,
    }
    for name, df in dfs.items():
        for col in _REQUIRED_COLUMNS[name]:
            if col not in df.columns:
                raise ValueError(f"必須カラムがありません: {name}.{col}")

    truck_cost_rows = parameters_df.loc[parameters_df["項目"] == "配送費_車両", "数量"]
    if truck_cost_rows.empty:
        raise ValueError("必須パラメータがありません: 配送費_車両")

    pm = product_master_df.set_index("商品コード")
    ts = time_series_df.set_index(["商品コード", "日付"])
    inv = inventory_init_df.set_index("商品コード")

    return {
        "products_list": sorted(pm.index.tolist()),
        "days_list": sorted(time_series_df["日付"].unique().tolist()),
        "holding_cost": pm["在庫コスト"].to_dict(),
        "cost_per_case": pm["配送費_ケース"].to_dict(),
        "cost_per_truck": float(truck_cost_rows.iloc[0]),
        "max_cases_per_truck": pm["CS/車両"].to_dict(),
        "x_bar": ts["入荷予定"].to_dict(),
        "shipping_forecast": ts["出荷予測"].to_dict(),
        "inventory_init": inv["前日末在庫"].to_dict(),
        "cumulative_shippable_qty": ts["出荷可能数累計"].to_dict(),
    }


def _build_result(products_list, days_list, x_small_values, x_large_values, n_trucks_values, inventory_values):
    rows = []
    for d in days_list:
        for p in products_list:
            small = x_small_values[(p, d)]
            large = x_large_values[(p, d)]
            rows.append({
                "日付": d,
                "商品コード": p,
                "小口入荷数": small,
                "大口入荷数": large,
                "入荷数合計": small + large,
                "在庫": inventory_values[(p, d)],
            })

    decision_variables_df = pd.DataFrame(rows, columns=["日付", "商品コード", "小口入荷数", "大口入荷数", "入荷数合計", "在庫"])

    trucks_df = pd.DataFrame([
        {"日付": d, "トラック台数": int(round(n_trucks_values[d]))}
        for d in days_list
    ], columns=["日付", "トラック台数"])

    return decision_variables_df, trucks_df


def load_excel(excel_path):
    with pd.ExcelFile(Path(excel_path)) as xlsx:
        for sheet_name in SHEET_NAMES:
            if sheet_name not in xlsx.sheet_names:
                raise ValueError(f"必須シートがありません: {sheet_name}")
        return {key: xlsx.parse(sheet) for sheet, key in SHEET_NAMES.items()}
