import pytest
import pandas as pd
from optimizer import load_excel, _prepare_inputs, _build_result, optimize, calculate_baseline, optimize_fixed_order


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
    assert result["order_unit"] == {"A": 1, "B": 1}


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


# ── _build_result ──────────────────────────────────────────────────


@pytest.fixture
def sample_br_inputs():
    products_list = ["A", "B"]
    days_list = [pd.Timestamp("2024-01-01"), pd.Timestamp("2024-01-02")]
    x_small = {
        ("A", pd.Timestamp("2024-01-01")): 5.0,
        ("A", pd.Timestamp("2024-01-02")): 3.0,
        ("B", pd.Timestamp("2024-01-01")): 8.0,
        ("B", pd.Timestamp("2024-01-02")): 2.0,
    }
    x_large = {
        ("A", pd.Timestamp("2024-01-01")): 0.0,
        ("A", pd.Timestamp("2024-01-02")): 10.0,
        ("B", pd.Timestamp("2024-01-01")): 0.0,
        ("B", pd.Timestamp("2024-01-02")): 5.0,
    }
    n_trucks = {
        pd.Timestamp("2024-01-01"): 0.0,
        pd.Timestamp("2024-01-02"): 2.0,
    }
    inventory = {
        ("A", pd.Timestamp("2024-01-01")): 10.0,
        ("A", pd.Timestamp("2024-01-02")): 7.0,
        ("B", pd.Timestamp("2024-01-01")): 12.0,
        ("B", pd.Timestamp("2024-01-02")): 9.0,
    }
    return products_list, days_list, x_small, x_large, n_trucks, inventory


def test_BR_1_returns_two_dataframes(sample_br_inputs):
    result = _build_result(*sample_br_inputs)

    assert isinstance(result, tuple)
    assert len(result) == 2
    decision_variables_df, trucks_df = result
    assert isinstance(decision_variables_df, pd.DataFrame)
    assert isinstance(trucks_df, pd.DataFrame)


def test_BR_2_decision_variables_schema(sample_br_inputs):
    decision_variables_df, _ = _build_result(*sample_br_inputs)

    assert list(decision_variables_df.columns) == ["日付", "商品コード", "小口入荷数", "大口入荷数", "入荷数合計", "在庫"]
    assert len(decision_variables_df) == 4  # 2 products × 2 days


def test_BR_3_total_arrival_equals_sum_of_small_and_large(sample_br_inputs):
    decision_variables_df, _ = _build_result(*sample_br_inputs)

    for _, row in decision_variables_df.iterrows():
        assert row["入荷数合計"] == pytest.approx(row["小口入荷数"] + row["大口入荷数"])


def test_BR_4_specific_values_in_decision_variables(sample_br_inputs):
    decision_variables_df, _ = _build_result(*sample_br_inputs)

    row = decision_variables_df[
        (decision_variables_df["日付"] == pd.Timestamp("2024-01-02")) &
        (decision_variables_df["商品コード"] == "A")
    ].iloc[0]

    assert row["小口入荷数"] == pytest.approx(3.0)
    assert row["大口入荷数"] == pytest.approx(10.0)
    assert row["入荷数合計"] == pytest.approx(13.0)
    assert row["在庫"] == pytest.approx(7.0)


def test_BR_5_trucks_schema_and_values(sample_br_inputs):
    _, trucks_df = _build_result(*sample_br_inputs)

    assert list(trucks_df.columns) == ["日付", "トラック台数"]
    assert len(trucks_df) == 2  # 2 days
    assert pd.api.types.is_integer_dtype(trucks_df["トラック台数"])
    assert trucks_df.loc[trucks_df["日付"] == pd.Timestamp("2024-01-02"), "トラック台数"].values[0] == 2


# ── O-1: optimize ─────────────────────────────────────────────────


def test_O1_1_returns_optimal_status(sample_dfs):
    result = optimize(*sample_dfs)

    assert result["status"] == "Optimal"


def test_O1_2_output_schema(sample_dfs):
    result = optimize(*sample_dfs)

    assert set(result.keys()) == {"status", "total_cost", "cost_breakdown", "decision_variables", "trucks"}
    assert isinstance(result["total_cost"], float)
    assert set(result["cost_breakdown"].keys()) == {"delivery_small", "delivery_large", "holding"}
    assert isinstance(result["decision_variables"], pd.DataFrame)
    assert isinstance(result["trucks"], pd.DataFrame)


def test_O1_3_cost_breakdown_sums_to_total(sample_dfs):
    result = optimize(*sample_dfs)

    breakdown = result["cost_breakdown"]
    expected = breakdown["delivery_small"] + breakdown["delivery_large"] + breakdown["holding"]
    assert result["total_cost"] == pytest.approx(expected)


def test_O1_4_inventory_non_negative(sample_dfs):
    result = optimize(*sample_dfs)

    assert (result["decision_variables"]["在庫"] >= -1e-6).all()


def test_O1_5_optimal_cost_value(sample_dfs):
    # sample_dfs では累積制約により全入荷が x_bar に固定 → total_cost = 3737.0
    result = optimize(*sample_dfs)

    assert result["total_cost"] == pytest.approx(3737.0)


# ── O-3: 制約条件の正確性 ─────────────────────────────────────────


@pytest.fixture
def dfs_forcing_trucks():
    # ケース単価 500 >> トラック単価 100/5=20 → 最適解は大口入荷を選ぶ
    return (
        pd.DataFrame({"商品コード": ["T"], "在庫コスト": [0.0], "配送費_ケース": [500.0], "CS/車両": [5], "発注単位": [1]}),
        pd.DataFrame({"項目": ["配送費_車両"], "数量": [100]}),
        pd.DataFrame({"商品コード": ["T"], "日付": [pd.Timestamp("2024-01-01")],
                      "入荷予定": [10], "出荷予測": [0], "出荷可能数累計": [10]}),
        pd.DataFrame({"商品コード": ["T"], "前日末在庫": [0]}),
    )


def test_O3_1_inventory_transition(sample_dfs):
    product_master, parameters, time_series, inventory_init = sample_dfs
    result = optimize(product_master, parameters, time_series, inventory_init)
    dv = result["decision_variables"]

    shipping = time_series.set_index(["商品コード", "日付"])["出荷予測"].to_dict()
    init_inv = inventory_init.set_index("商品コード")["前日末在庫"].to_dict()
    days = sorted(time_series["日付"].unique())
    products = sorted(time_series["商品コード"].unique())

    for p in products:
        prev = init_inv[p]
        for d in days:
            row = dv[(dv["商品コード"] == p) & (dv["日付"] == d)].iloc[0]
            expected = prev + row["入荷数合計"] - shipping[(p, d)]
            assert row["在庫"] == pytest.approx(expected, abs=1e-6)
            prev = row["在庫"]


def test_O3_2_truck_capacity(dfs_forcing_trucks):
    result = optimize(*dfs_forcing_trucks)
    dv = result["decision_variables"]
    trucks = result["trucks"]

    d = pd.Timestamp("2024-01-01")
    n = trucks.loc[trucks["日付"] == d, "トラック台数"].values[0]
    x_large = dv.loc[(dv["日付"] == d) & (dv["商品コード"] == "T"), "大口入荷数"].values[0]

    assert x_large > 0  # 安いトラックを使うはず
    assert x_large / 5 <= n + 1e-6  # トラック容量制約


# ── O-4: エラーハンドリング ────────────────────────────────────────


@pytest.fixture
def dfs_infeasible():
    # x_bar=10 > cumulative_shippable=5 → 累積制約が矛盾して実行不可能
    return (
        pd.DataFrame({"商品コード": ["X"], "在庫コスト": [1.0], "配送費_ケース": [100.0], "CS/車両": [10], "発注単位": [1]}),
        pd.DataFrame({"項目": ["配送費_車両"], "数量": [1000]}),
        pd.DataFrame({"商品コード": ["X"], "日付": [pd.Timestamp("2024-01-01")],
                      "入荷予定": [10], "出荷予測": [5], "出荷可能数累計": [5]}),
        pd.DataFrame({"商品コード": ["X"], "前日末在庫": [0]}),
    )


def test_O4_1_no_solution(dfs_infeasible):
    result = optimize(*dfs_infeasible)

    assert result["status"] != "Optimal"
    assert result["total_cost"] is None
    assert result["cost_breakdown"] is None
    assert result["decision_variables"] is None
    assert result["trucks"] is None


def test_O4_2_invalid_input(sample_dfs):
    product_master, parameters, time_series, inventory_init = sample_dfs
    bad_product_master = product_master.drop(columns=["配送費_ケース"])

    with pytest.raises(ValueError, match="配送費_ケース"):
        optimize(bad_product_master, parameters, time_series, inventory_init)


# ── O-3: 制約条件の正確性 ─────────────────────────────────────────


def test_O3_3_cumulative_constraints(sample_dfs):
    product_master, parameters, time_series, inventory_init = sample_dfs
    result = optimize(product_master, parameters, time_series, inventory_init)
    dv = result["decision_variables"]

    x_bar = time_series.set_index(["商品コード", "日付"])["入荷予定"].to_dict()
    cum_shippable = time_series.set_index(["商品コード", "日付"])["出荷可能数累計"].to_dict()
    days = sorted(time_series["日付"].unique())
    products = sorted(time_series["商品コード"].unique())

    for p in products:
        cum_arrival = 0.0
        cum_x_bar_total = 0.0
        for d in days:
            row = dv[(dv["商品コード"] == p) & (dv["日付"] == d)].iloc[0]
            cum_arrival += row["入荷数合計"]
            cum_x_bar_total += x_bar[(p, d)]
            assert cum_arrival >= cum_x_bar_total - 1e-6
            assert cum_arrival <= cum_shippable[(p, d)] + 1e-6


# ── O-5: calculate_baseline ───────────────────────────────────────


def test_O5_1_returns_baseline_status(sample_dfs):
    result = calculate_baseline(*sample_dfs)

    assert result["status"] == "Baseline"


def test_O5_2_output_schema(sample_dfs):
    result = calculate_baseline(*sample_dfs)

    assert set(result.keys()) == {"status", "total_cost", "cost_breakdown", "decision_variables", "trucks"}
    assert isinstance(result["total_cost"], float)
    assert set(result["cost_breakdown"].keys()) == {"delivery_small", "delivery_large", "holding"}
    assert isinstance(result["decision_variables"], pd.DataFrame)
    assert isinstance(result["trucks"], pd.DataFrame)


def test_O5_3_no_trucks_no_large(sample_dfs):
    result = calculate_baseline(*sample_dfs)
    dv = result["decision_variables"]
    trucks = result["trucks"]

    assert (dv["大口入荷数"] == 0).all()
    assert (trucks["トラック台数"] == 0).all()


def test_O5_4_arrival_equals_x_bar(sample_dfs):
    product_master, parameters, time_series, inventory_init = sample_dfs
    result = calculate_baseline(product_master, parameters, time_series, inventory_init)
    dv = result["decision_variables"]

    x_bar = time_series.set_index(["商品コード", "日付"])["入荷予定"].to_dict()
    for _, row in dv.iterrows():
        assert row["小口入荷数"] == pytest.approx(x_bar[(row["商品コード"], row["日付"])])


def test_O5_5_cost_value(sample_dfs):
    result = calculate_baseline(*sample_dfs)

    # delivery_large = 0、total = delivery_small(3700) + holding(37) = 3737.0
    assert result["cost_breakdown"]["delivery_large"] == pytest.approx(0.0)
    assert result["total_cost"] == pytest.approx(3737.0)


# ── O-6: optimize_fixed_order ─────────────────────────────────────


def test_O6_1_returns_optimal_status(sample_dfs):
    result = optimize_fixed_order(*sample_dfs)

    assert result["status"] == "Optimal"


def test_O6_2_output_schema(sample_dfs):
    result = optimize_fixed_order(*sample_dfs)

    assert set(result.keys()) == {"status", "total_cost", "cost_breakdown", "decision_variables", "trucks"}
    assert isinstance(result["total_cost"], float)
    assert set(result["cost_breakdown"].keys()) == {"delivery_small", "delivery_large", "holding"}
    assert isinstance(result["decision_variables"], pd.DataFrame)
    assert isinstance(result["trucks"], pd.DataFrame)


def test_O6_3_total_arrival_equals_x_bar(sample_dfs):
    product_master, parameters, time_series, inventory_init = sample_dfs
    result = optimize_fixed_order(product_master, parameters, time_series, inventory_init)
    dv = result["decision_variables"]

    x_bar = time_series.set_index(["商品コード", "日付"])["入荷予定"].to_dict()
    for _, row in dv.iterrows():
        assert row["入荷数合計"] == pytest.approx(x_bar[(row["商品コード"], row["日付"])], abs=1e-6)


def test_O6_4_prefers_trucks_when_cheaper(dfs_forcing_trucks):
    # ケース単価 500 >> トラック単価 20 → x_large = 10、n_trucks = 2、total_cost = 200
    result = optimize_fixed_order(*dfs_forcing_trucks)
    dv = result["decision_variables"]

    d = pd.Timestamp("2024-01-01")
    x_large = dv.loc[(dv["日付"] == d) & (dv["商品コード"] == "T"), "大口入荷数"].values[0]
    assert x_large > 0
    assert result["total_cost"] == pytest.approx(200.0)


def test_O6_5_cost_value(sample_dfs):
    result = optimize_fixed_order(*sample_dfs)

    # sample_dfs はトラック不利 → x_small = x_bar → total_cost = 3737.0
    assert result["total_cost"] == pytest.approx(3737.0)


# ── O-7: 発注単位制約 ──────────────────────────────────────────────


@pytest.fixture
def dfs_with_order_unit():
    # 発注単位=5、x_bar=7、出荷=7、在庫初期=0
    # → 在庫非負を維持できる最小の発注単位倍数 = 10（5 では在庫が負）
    return (
        pd.DataFrame({"商品コード": ["U"], "在庫コスト": [0.0], "配送費_ケース": [100.0], "CS/車両": [50], "発注単位": [5]}),
        pd.DataFrame({"項目": ["配送費_車両"], "数量": [99999]}),
        pd.DataFrame({
            "商品コード": ["U"],
            "日付": [pd.Timestamp("2024-01-01")],
            "入荷予定": [7],
            "出荷予測": [7],
            "出荷可能数累計": [10],
        }),
        pd.DataFrame({"商品コード": ["U"], "前日末在庫": [0]}),
    )


def test_O7_1_order_quantity_is_multiple_of_unit(dfs_with_order_unit):
    result = optimize(*dfs_with_order_unit)

    assert result["status"] == "Optimal"
    dv = result["decision_variables"]
    assert dv.iloc[0]["入荷数合計"] == pytest.approx(10.0)


@pytest.fixture
def dfs_with_order_unit_each():
    # order_unit=5, K_p=8 (truck holds 8), case_cost=1, truck_cost=3
    # Old constraint (sum=5k): x_large=8, x_small=2 (1 truck + 2 cases = cost 5) is optimal
    # New constraint (each=5k): x_large must be 0/5/10 → x_large=10 (2 trucks, cost=6) is optimal
    return (
        pd.DataFrame({"商品コード": ["V"], "在庫コスト": [0.0], "配送費_ケース": [1.0], "CS/車両": [8], "発注単位": [5]}),
        pd.DataFrame({"項目": ["配送費_車両"], "数量": [3]}),
        pd.DataFrame({
            "商品コード": ["V"],
            "日付": [pd.Timestamp("2024-01-01")],
            "入荷予定": [10],
            "出荷予測": [10],
            "出荷可能数累計": [10],
        }),
        pd.DataFrame({"商品コード": ["V"], "前日末在庫": [0]}),
    )


def test_O7_2_each_variable_is_multiple_of_unit(dfs_with_order_unit_each):
    result = optimize(*dfs_with_order_unit_each)

    assert result["status"] == "Optimal"
    dv = result["decision_variables"]
    row = dv.iloc[0]
    assert row["小口入荷数"] % 5 == pytest.approx(0.0, abs=1e-6)
    assert row["大口入荷数"] % 5 == pytest.approx(0.0, abs=1e-6)
    # 旧制約では x_large=8 (多く積める1台) が最適になるが、
    # 新制約では 5 の倍数のみ許容 → x_large=10 (2台) が最適
    assert row["大口入荷数"] == pytest.approx(10.0)
    assert row["小口入荷数"] == pytest.approx(0.0)
