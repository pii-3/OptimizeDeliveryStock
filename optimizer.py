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


def optimize(
    product_master_df: pd.DataFrame,
    parameters_df: pd.DataFrame,
    time_series_df: pd.DataFrame,
    inventory_init_df: pd.DataFrame,
) -> dict:
    # 集合
    products_list = (
        time_series_df["商品コード"].drop_duplicates().sort_values().to_list()
    )
    days_list = (
        time_series_df["日付"].drop_duplicates().sort_values().to_list()
    )

    # 定数
    holding_cost_dict = (
        product_master_df.set_index("商品コード")["在庫コスト"].to_dict()
    )
    cost_per_case_dict = (
        product_master_df.set_index("商品コード")["配送費_ケース"].to_dict()
    )
    cost_per_truck = (
        parameters_df.set_index("項目").loc["配送費_車両", "数量"]
    )
    max_cases_per_truck_dict = (
        product_master_df.set_index("商品コード")["CS/車両"].to_dict()
    )

    # 入力データ
    x_bar_dict = (
        time_series_df.set_index(["商品コード", "日付"])["入荷予定"]
        .fillna(0)
        .to_dict()
    )
    shipping_forecast_dict = (
        time_series_df.set_index(["商品コード", "日付"])["出荷予測"]
        .fillna(0)
        .to_dict()
    )
    inventory_init_dict = (
        inventory_init_df.set_index("商品コード")["前日末在庫"].to_dict()
    )
    cumulative_shippable_qty_dict = (
        time_series_df.set_index(["商品コード", "日付"])["出荷可能数累計"]
        .fillna(0)
        .to_dict()
    )

    # モデル
    model = pulp.LpProblem("Delivery_Stock_Optimization", pulp.LpMinimize)

    # 変数
    x_small = pulp.LpVariable.dicts(
        "x_small", (products_list, days_list), lowBound=0
    )
    x_large = pulp.LpVariable.dicts(
        "x_large", (products_list, days_list), lowBound=0
    )
    n_trucks = pulp.LpVariable.dicts(
        "n_trucks", days_list, lowBound=0, cat="Integer"
    )
    I = pulp.LpVariable.dicts(
        "Inventory", (products_list, days_list), lowBound=0
    )

    # 目的関数
    model += (
        pulp.lpSum(
            cost_per_case_dict[p] * x_small[p][d]
            for p in products_list
            for d in days_list
        )
        + pulp.lpSum(cost_per_truck * n_trucks[d] for d in days_list)
        + pulp.lpSum(
            holding_cost_dict[p] * I[p][d]
            for p in products_list
            for d in days_list
        )
    )

    # 制約条件
    for d_idx, d in enumerate(days_list):
        tau_list = days_list[: d_idx + 1]

        # トラック容量（混載）
        model += (
            pulp.lpSum(
                x_large[p][d] / max_cases_per_truck_dict[p]
                for p in products_list
            )
            <= n_trucks[d]
        )

        # 日次の入荷合計 ≥ ベース入荷数合計
        model += pulp.lpSum(
            x_small[p][d] + x_large[p][d] for p in products_list
        ) >= pulp.lpSum(x_bar_dict[(p, d)] for p in products_list)

        for p in products_list:
            # 在庫推移
            if d_idx == 0:
                model += I[p][d] == (
                    inventory_init_dict[p]
                    + x_small[p][d]
                    + x_large[p][d]
                    - shipping_forecast_dict[(p, d)]
                )
            else:
                d_prev = days_list[d_idx - 1]
                model += I[p][d] == (
                    I[p][d_prev]
                    + x_small[p][d]
                    + x_large[p][d]
                    - shipping_forecast_dict[(p, d)]
                )

            # 累積入荷数 ≥ 累積ベース入荷数（前倒しのみ可能）
            model += pulp.lpSum(
                x_small[p][tau] + x_large[p][tau] for tau in tau_list
            ) >= pulp.lpSum(x_bar_dict[(p, tau)] for tau in tau_list)

            # 累積入荷数 ≤ 出荷可能数累計
            model += pulp.lpSum(
                x_small[p][tau] + x_large[p][tau] for tau in tau_list
            ) <= cumulative_shippable_qty_dict[(p, d)]

    # 求解
    model.solve(pulp.PULP_CBC_CMD(msg=0))

    status = pulp.LpStatus[model.status]
    total_cost = pulp.value(model.objective)

    if model.status != pulp.LpStatusOptimal:
        return {"status": status, "total_cost": None, "decision_variables": None, "trucks": None}

    # 結果の整形
    decision_variables_df = pd.DataFrame([
        {
            "日付": d,
            "商品コード": p,
            "小口入荷数": x_small[p][d].value(),
            "大口入荷数": x_large[p][d].value(),
            "入荷数合計": x_small[p][d].value() + x_large[p][d].value(),
            "在庫": I[p][d].value(),
        }
        for d in days_list
        for p in products_list
    ])

    trucks_df = pd.DataFrame([
        {"日付": d, "トラック台数": n_trucks[d].value()}
        for d in days_list
    ])

    return {
        "status": status,
        "total_cost": total_cost,
        "decision_variables": decision_variables_df,
        "trucks": trucks_df,
    }
