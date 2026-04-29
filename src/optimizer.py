import pandas as pd
import pulp


def load_excel(excel_path: str) -> dict[str, pd.DataFrame]:
    dfs = pd.read_excel(excel_path, sheet_name=None)
    return {
        "product_master": dfs["商品マスタ"],
        "parameters": dfs["パラメータ"],
        "time_series": dfs["時系列データ"],
        "inventory_init": dfs["前日末在庫"],
    }


def _prepare_inputs(
    product_master_df: pd.DataFrame,
    parameters_df: pd.DataFrame,
    time_series_df: pd.DataFrame,
    inventory_init_df: pd.DataFrame,
) -> dict:
    return {
        "products_list": (
            time_series_df["商品コード"].drop_duplicates().sort_values().to_list()
        ),
        "days_list": (
            time_series_df["日付"].drop_duplicates().sort_values().to_list()
        ),
        "holding_cost": (
            product_master_df.set_index("商品コード")["在庫コスト"].to_dict()
        ),
        "cost_per_case": (
            product_master_df.set_index("商品コード")["配送費_ケース"].to_dict()
        ),
        "cost_per_truck": float(
            parameters_df.set_index("項目").loc["配送費_車両", "数量"]
        ),
        "max_cases_per_truck": (
            product_master_df.set_index("商品コード")["CS/車両"].to_dict()
        ),
        "x_bar": (
            time_series_df.set_index(["商品コード", "日付"])["入荷予定"]
            .fillna(0)
            .to_dict()
        ),
        "shipping_forecast": (
            time_series_df.set_index(["商品コード", "日付"])["出荷予測"]
            .fillna(0)
            .to_dict()
        ),
        "inventory_init": (
            inventory_init_df.set_index("商品コード")["前日末在庫"].to_dict()
        ),
        "cumulative_shippable_qty": (
            time_series_df.set_index(["商品コード", "日付"])["出荷可能数累計"]
            .fillna(0)
            .to_dict()
        ),
    }


def _build_result(
    products_list: list,
    days_list: list,
    x_small_values: dict,
    x_large_values: dict,
    n_trucks_values: dict,
    inventory_values: dict,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    decision_variables_df = pd.DataFrame([
        {
            "日付": d,
            "商品コード": p,
            "小口入荷数": x_small_values[(p, d)],
            "大口入荷数": x_large_values[(p, d)],
            "入荷数合計": x_small_values[(p, d)] + x_large_values[(p, d)],
            "在庫": inventory_values[(p, d)],
        }
        for d in days_list
        for p in products_list
    ])

    trucks_df = pd.DataFrame([
        {"日付": d, "トラック台数": n_trucks_values[d]}
        for d in days_list
    ])

    return decision_variables_df, trucks_df


def optimize(
    product_master_df: pd.DataFrame,
    parameters_df: pd.DataFrame,
    time_series_df: pd.DataFrame,
    inventory_init_df: pd.DataFrame,
) -> dict:
    inp = _prepare_inputs(product_master_df, parameters_df, time_series_df, inventory_init_df)
    products_list = inp["products_list"]
    days_list = inp["days_list"]

    model = pulp.LpProblem("Delivery_Stock_Optimization", pulp.LpMinimize)

    x_small = pulp.LpVariable.dicts("x_small", (products_list, days_list), lowBound=0)
    x_large = pulp.LpVariable.dicts("x_large", (products_list, days_list), lowBound=0)
    n_trucks = pulp.LpVariable.dicts("n_trucks", days_list, lowBound=0, cat="Integer")
    I = pulp.LpVariable.dicts("Inventory", (products_list, days_list), lowBound=0)

    model += (
        pulp.lpSum(inp["cost_per_case"][p] * x_small[p][d] for p in products_list for d in days_list)
        + pulp.lpSum(inp["cost_per_truck"] * n_trucks[d] for d in days_list)
        + pulp.lpSum(inp["holding_cost"][p] * I[p][d] for p in products_list for d in days_list)
    )

    for d_idx, d in enumerate(days_list):
        tau_list = days_list[: d_idx + 1]

        model += (
            pulp.lpSum(x_large[p][d] / inp["max_cases_per_truck"][p] for p in products_list)
            <= n_trucks[d]
        )

        for p in products_list:
            if d_idx == 0:
                model += I[p][d] == (
                    inp["inventory_init"][p] + x_small[p][d] + x_large[p][d] - inp["shipping_forecast"][(p, d)]
                )
            else:
                d_prev = days_list[d_idx - 1]
                model += I[p][d] == (
                    I[p][d_prev] + x_small[p][d] + x_large[p][d] - inp["shipping_forecast"][(p, d)]
                )

            model += (
                pulp.lpSum(x_small[p][tau] + x_large[p][tau] for tau in tau_list)
                >= pulp.lpSum(inp["x_bar"][(p, tau)] for tau in tau_list)
            )

            model += (
                pulp.lpSum(x_small[p][tau] + x_large[p][tau] for tau in tau_list)
                <= inp["cumulative_shippable_qty"][(p, d)]
            )

    model.solve(pulp.PULP_CBC_CMD(msg=0))

    status = pulp.LpStatus[model.status]
    if model.status != pulp.LpStatusOptimal:
        return {"status": status, "total_cost": None, "decision_variables": None, "trucks": None}

    decision_variables_df, trucks_df = _build_result(
        products_list,
        days_list,
        x_small_values={(p, d): x_small[p][d].value() for p in products_list for d in days_list},
        x_large_values={(p, d): x_large[p][d].value() for p in products_list for d in days_list},
        n_trucks_values={d: n_trucks[d].value() for d in days_list},
        inventory_values={(p, d): I[p][d].value() for p in products_list for d in days_list},
    )

    return {
        "status": status,
        "total_cost": pulp.value(model.objective),
        "decision_variables": decision_variables_df,
        "trucks": trucks_df,
    }


def calculate_baseline(
    product_master_df: pd.DataFrame,
    parameters_df: pd.DataFrame,
    time_series_df: pd.DataFrame,
    inventory_init_df: pd.DataFrame,
) -> dict:
    inp = _prepare_inputs(product_master_df, parameters_df, time_series_df, inventory_init_df)
    products_list = inp["products_list"]
    days_list = inp["days_list"]

    x_small_values = {(p, d): inp["x_bar"][(p, d)] for p in products_list for d in days_list}
    x_large_values = {(p, d): 0.0 for p in products_list for d in days_list}
    n_trucks_values = {d: 0.0 for d in days_list}

    inventory_values = {}
    for p in products_list:
        i_prev = inp["inventory_init"][p]
        for d in days_list:
            i_prev = i_prev + x_small_values[(p, d)] - inp["shipping_forecast"][(p, d)]
            inventory_values[(p, d)] = i_prev

    total_cost = sum(
        inp["cost_per_case"][p] * x_small_values[(p, d)]
        + inp["holding_cost"][p] * inventory_values[(p, d)]
        for p in products_list
        for d in days_list
    )

    decision_variables_df, trucks_df = _build_result(
        products_list, days_list,
        x_small_values=x_small_values,
        x_large_values=x_large_values,
        n_trucks_values=n_trucks_values,
        inventory_values=inventory_values,
    )

    return {
        "status": "Baseline",
        "total_cost": total_cost,
        "decision_variables": decision_variables_df,
        "trucks": trucks_df,
    }
