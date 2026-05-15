import pandas as pd
import pulp
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


def optimize(product_master_df, parameters_df, time_series_df, inventory_init_df):
    inp = _prepare_inputs(product_master_df, parameters_df, time_series_df, inventory_init_df)
    P = inp["products_list"]
    D = inp["days_list"]

    model = pulp.LpProblem("OptimizeDelivery", pulp.LpMinimize)

    x_small = {(p, d): pulp.LpVariable(f"x_small_{p}_{d}", lowBound=0) for p in P for d in D}
    x_large = {(p, d): pulp.LpVariable(f"x_large_{p}_{d}", lowBound=0) for p in P for d in D}
    n_trucks = {d: pulp.LpVariable(f"n_trucks_{d}", lowBound=0, cat="Integer") for d in D}
    inventory = {(p, d): pulp.LpVariable(f"inv_{p}_{d}", lowBound=0) for p in P for d in D}

    model += pulp.lpSum(
        inp["cost_per_case"][p] * x_small[(p, d)]
        + inp["holding_cost"][p] * inventory[(p, d)]
        for p in P for d in D
    ) + pulp.lpSum(inp["cost_per_truck"] * n_trucks[d] for d in D)

    for p in P:
        for i, d in enumerate(D):
            prev_inv = inp["inventory_init"][p] if i == 0 else inventory[(p, D[i - 1])]
            model += inventory[(p, d)] == prev_inv + x_small[(p, d)] + x_large[(p, d)] - inp["shipping_forecast"][(p, d)]

    for d in D:
        model += pulp.lpSum(x_large[(p, d)] / inp["max_cases_per_truck"][p] for p in P) <= n_trucks[d]

    for p in P:
        for i, d in enumerate(D):
            cum_arrival = pulp.lpSum(x_small[(p, D[j])] + x_large[(p, D[j])] for j in range(i + 1))
            cum_x_bar = sum(inp["x_bar"][(p, D[j])] for j in range(i + 1))
            model += cum_arrival >= cum_x_bar
            model += cum_arrival <= inp["cumulative_shippable_qty"][(p, d)]

    model.solve(pulp.PULP_CBC_CMD(msg=0))

    status = pulp.LpStatus[model.status]
    if status != "Optimal":
        return {"status": status, "total_cost": None, "cost_breakdown": None, "decision_variables": None, "trucks": None}

    x_small_val = {k: v.value() for k, v in x_small.items()}
    x_large_val = {k: v.value() for k, v in x_large.items()}
    n_trucks_val = {k: v.value() for k, v in n_trucks.items()}
    inv_val = {k: v.value() for k, v in inventory.items()}

    delivery_small = sum(inp["cost_per_case"][p] * x_small_val[(p, d)] for p in P for d in D)
    delivery_large = sum(inp["cost_per_truck"] * n_trucks_val[d] for d in D)
    holding = sum(inp["holding_cost"][p] * inv_val[(p, d)] for p in P for d in D)

    decision_variables_df, trucks_df = _build_result(P, D, x_small_val, x_large_val, n_trucks_val, inv_val)

    return {
        "status": "Optimal",
        "total_cost": float(delivery_small + delivery_large + holding),
        "cost_breakdown": {
            "delivery_small": float(delivery_small),
            "delivery_large": float(delivery_large),
            "holding": float(holding),
        },
        "decision_variables": decision_variables_df,
        "trucks": trucks_df,
    }


def calculate_baseline(product_master_df, parameters_df, time_series_df, inventory_init_df):
    inp = _prepare_inputs(product_master_df, parameters_df, time_series_df, inventory_init_df)
    P = inp["products_list"]
    D = inp["days_list"]

    x_small_val = {(p, d): float(inp["x_bar"][(p, d)]) for p in P for d in D}
    x_large_val = {(p, d): 0.0 for p in P for d in D}
    n_trucks_val = {d: 0.0 for d in D}

    inv_val = {}
    for p in P:
        prev = inp["inventory_init"][p]
        for d in D:
            inv_val[(p, d)] = prev + x_small_val[(p, d)] - inp["shipping_forecast"][(p, d)]
            prev = inv_val[(p, d)]

    delivery_small = sum(inp["cost_per_case"][p] * x_small_val[(p, d)] for p in P for d in D)
    holding = sum(inp["holding_cost"][p] * inv_val[(p, d)] for p in P for d in D)

    decision_variables_df, trucks_df = _build_result(P, D, x_small_val, x_large_val, n_trucks_val, inv_val)

    return {
        "status": "Baseline",
        "total_cost": float(delivery_small + holding),
        "cost_breakdown": {
            "delivery_small": float(delivery_small),
            "delivery_large": 0.0,
            "holding": float(holding),
        },
        "decision_variables": decision_variables_df,
        "trucks": trucks_df,
    }


def load_excel(excel_path):
    with pd.ExcelFile(Path(excel_path)) as xlsx:
        for sheet_name in SHEET_NAMES:
            if sheet_name not in xlsx.sheet_names:
                raise ValueError(f"必須シートがありません: {sheet_name}")
        return {key: xlsx.parse(sheet) for sheet, key in SHEET_NAMES.items()}
