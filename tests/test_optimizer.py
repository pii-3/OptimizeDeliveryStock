import pytest
import pandas as pd
from optimizer import load_excel, optimize


# ---------------------------------------------------------------------------
# 内部ヘルパー: _prepare_inputs()
# ---------------------------------------------------------------------------

class TestPrepareInputs:
    """内部ヘルパー _prepare_inputs() の出力契約"""

    @pytest.fixture
    def prepared(self, simple_input_data):
        from optimizer import _prepare_inputs
        return _prepare_inputs(
            simple_input_data["product_master"],
            simple_input_data["parameters"],
            simple_input_data["time_series"],
            simple_input_data["inventory_init"],
        )

    def test_returns_required_keys(self, prepared):
        """必要なキーがすべて揃っている"""
        expected_keys = {
            "products_list", "days_list",
            "holding_cost", "cost_per_case", "cost_per_truck",
            "max_cases_per_truck", "x_bar", "shipping_forecast",
            "inventory_init", "cumulative_shippable_qty",
        }
        assert set(prepared.keys()) == expected_keys

    def test_products_list_is_sorted(self, prepared):
        """products_list がソート済み"""
        assert prepared["products_list"] == sorted(prepared["products_list"])

    def test_days_list_is_sorted(self, prepared):
        """days_list がソート済み"""
        assert prepared["days_list"] == sorted(prepared["days_list"])

    def test_x_bar_keys_are_product_date_tuples(self, prepared):
        """x_bar のキーが (商品コード, 日付) のタプル"""
        for key in prepared["x_bar"]:
            assert isinstance(key, tuple) and len(key) == 2

    def test_cost_per_truck_is_scalar(self, prepared):
        """cost_per_truck がスカラー値"""
        assert isinstance(prepared["cost_per_truck"], (int, float))


# ---------------------------------------------------------------------------
# 内部ヘルパー: _build_result()
# ---------------------------------------------------------------------------

class TestBuildResult:
    """内部ヘルパー _build_result() の出力契約"""

    @pytest.fixture
    def build_inputs(self):
        """_build_result() テスト用の数値入力"""
        dates = pd.date_range("2026-01-01", periods=2).tolist()
        return {
            "products_list": ["P001"],
            "days_list": dates,
            "x_small_values": {("P001", d): 10.0 for d in dates},
            "x_large_values": {("P001", d): 0.0 for d in dates},
            "n_trucks_values": {d: 0.0 for d in dates},
            "inventory_values": {("P001", d): 5.0 for d in dates},
        }

    @pytest.fixture
    def built(self, build_inputs):
        from optimizer import _build_result
        return _build_result(**build_inputs)

    def test_returns_two_dataframes(self, built):
        """戻り値が (DataFrame, DataFrame) のタプル"""
        dv_df, trucks_df = built
        assert isinstance(dv_df, pd.DataFrame)
        assert isinstance(trucks_df, pd.DataFrame)

    def test_decision_variables_columns(self, built):
        """decision_variables のカラムが仕様通り"""
        dv_df, _ = built
        assert set(dv_df.columns) == {"日付", "商品コード", "小口入荷数", "大口入荷数", "入荷数合計", "在庫"}

    def test_trucks_columns(self, built):
        """trucks のカラムが仕様通り"""
        _, trucks_df = built
        assert set(trucks_df.columns) == {"日付", "トラック台数"}

    def test_nyuuka_total_is_sum(self, built):
        """入荷数合計 = 小口入荷数 + 大口入荷数"""
        dv_df, _ = built
        diff = (dv_df["入荷数合計"] - (dv_df["小口入荷数"] + dv_df["大口入荷数"])).abs()
        assert (diff < 0.01).all()


# ---------------------------------------------------------------------------
# 要件 O-1: 最適化関数
# ---------------------------------------------------------------------------

class TestO1_OptimizeFunctionStructure:
    """要件 O-1: 最適化関数の返り値構造"""

    @pytest.fixture
    def result(self, sample_input_data):
        return optimize(
            sample_input_data["product_master"],
            sample_input_data["parameters"],
            sample_input_data["time_series"],
            sample_input_data["inventory_init"],
        )

    def test_O1_returns_dict(self, result):
        """最適化関数が辞書を返す"""
        assert isinstance(result, dict)

    def test_O1_has_required_keys(self, result):
        """返り値に必要なキーが全て含まれる"""
        assert set(result.keys()) == {"status", "total_cost", "decision_variables", "trucks"}

    def test_O1_status_is_optimal(self, result):
        """最適解が見つかる"""
        assert result["status"] == "Optimal"

    def test_O1_total_cost_is_positive_float(self, result):
        """総コストが正の数値"""
        assert isinstance(result["total_cost"], (int, float))
        assert result["total_cost"] > 0

    def test_O1_decision_variables_columns(self, result):
        """decision_variables のカラムが仕様通り"""
        expected = {"日付", "商品コード", "小口入荷数", "大口入荷数", "入荷数合計", "在庫"}
        assert set(result["decision_variables"].columns) == expected

    def test_O1_trucks_columns(self, result):
        """trucks のカラムが仕様通り"""
        assert set(result["trucks"].columns) == {"日付", "トラック台数"}


# ---------------------------------------------------------------------------
# 要件 O-2: Excel ローダー
# ---------------------------------------------------------------------------

class TestO2_ExcelLoader:
    """要件 O-2: Excel ローダー"""

    @pytest.fixture
    def result(self):
        return load_excel("data/input/InputData.xlsx")

    def test_O2_load_excel_returns_dict(self, result):
        """load_excel が辞書を返す"""
        assert isinstance(result, dict)

    def test_O2_has_required_keys(self, result):
        """返り値に必要なキーが全て含まれる"""
        assert set(result.keys()) == {"product_master", "parameters", "time_series", "inventory_init"}

    def test_O2_all_values_are_dataframe(self, result):
        """全ての値が DataFrame"""
        for key, value in result.items():
            assert isinstance(value, pd.DataFrame), f"{key} is not DataFrame"


# ---------------------------------------------------------------------------
# 要件 O-3: 制約条件の正確性
# ---------------------------------------------------------------------------

class TestO3_ConstraintAccuracy:
    """要件 O-3: 制約条件の正確性

    simple_input_data の期待する最適解:
      x_small = 10 / 日、x_large = 0、在庫 = 0 / 日
    """

    def test_O3_1_inventory_transition_all_days(self, simple_result, simple_input_data):
        """在庫推移制約（全日）: I_{p,d} = I_{p,d-1} + x_{p,d} - s_{p,d}"""
        dv = simple_result["decision_variables"]
        ts = simple_input_data["time_series"].set_index(["商品コード", "日付"])
        inv_init = simple_input_data["inventory_init"].set_index("商品コード")

        for p in dv["商品コード"].unique():
            df_p = dv[dv["商品コード"] == p].sort_values("日付").reset_index(drop=True)
            for i, row in df_p.iterrows():
                d = row["日付"]
                s = ts.loc[(p, d), "出荷予測"]
                i_prev = inv_init.loc[p, "前日末在庫"] if i == 0 else df_p.loc[i - 1, "在庫"]
                expected = i_prev + row["入荷数合計"] - s
                assert abs(row["在庫"] - expected) < 0.01, f"{p} {d}: expected {expected}, got {row['在庫']}"

    def test_O3_1_inventory_all_nonnegative(self, sample_decision_variables):
        """全ての在庫が非負（実データで検証）"""
        assert (sample_decision_variables["在庫"] >= -0.01).all()

    def test_O3_2_truck_capacity_respected(self, simple_result, simple_input_data):
        """トラック容量制約: sum(x_large / K_p) <= n_trucks（全日）"""
        dv = simple_result["decision_variables"]
        trucks = simple_result["trucks"].set_index("日付")
        K = simple_input_data["product_master"].set_index("商品コード")["CS/車両"]

        for day, day_data in dv.groupby("日付"):
            usage = sum(row["大口入荷数"] / K[row["商品コード"]] for _, row in day_data.iterrows())
            assert usage <= trucks.loc[day, "トラック台数"] + 0.01, \
                f"{day}: usage {usage} > n_trucks {trucks.loc[day, 'トラック台数']}"

    def test_O3_3_cumulative_lower_bound(self, simple_result, simple_input_data):
        """累積入荷数 >= 累積入荷予定（前倒しのみ可能）（全商品・全日）"""
        dv = simple_result["decision_variables"]
        ts = simple_input_data["time_series"]

        for p in dv["商品コード"].unique():
            dates = sorted(dv["日付"].unique())
            for i, d in enumerate(dates):
                tau = dates[: i + 1]
                cum_x = dv[(dv["商品コード"] == p) & (dv["日付"].isin(tau))]["入荷数合計"].sum()
                cum_x_bar = ts[(ts["商品コード"] == p) & (ts["日付"].isin(tau))]["入荷予定"].sum()
                assert cum_x >= cum_x_bar - 0.01, f"{p} {d}: cum_x {cum_x} < cum_x_bar {cum_x_bar}"

    def test_O3_3_cumulative_upper_bound(self, simple_result, simple_input_data):
        """累積入荷数 <= 出荷可能数累計（全商品・全日）"""
        dv = simple_result["decision_variables"]
        ts = simple_input_data["time_series"].set_index(["商品コード", "日付"])

        for p in dv["商品コード"].unique():
            dates = sorted(dv["日付"].unique())
            for i, d in enumerate(dates):
                tau = dates[: i + 1]
                cum_x = dv[(dv["商品コード"] == p) & (dv["日付"].isin(tau))]["入荷数合計"].sum()
                shippable = ts.loc[(p, d), "出荷可能数累計"]
                assert cum_x <= shippable + 0.01, f"{p} {d}: cum_x {cum_x} > shippable {shippable}"


# ---------------------------------------------------------------------------
# 要件 O-4: エラーハンドリング
# ---------------------------------------------------------------------------

class TestO4_ErrorHandling:
    """要件 O-4: エラーハンドリング"""

    def test_O4_1_no_solution(self, infeasible_input_data):
        """最適解が見つからない場合 → status が Optimal 以外、数値フィールドは None"""
        result = optimize(
            infeasible_input_data["product_master"],
            infeasible_input_data["parameters"],
            infeasible_input_data["time_series"],
            infeasible_input_data["inventory_init"],
        )
        assert result["status"] != "Optimal"
        assert result["total_cost"] is None
        assert result["decision_variables"] is None
        assert result["trucks"] is None

    def test_O4_2_missing_column(self):
        """必須カラムなしの DataFrame → エラー発生"""
        bad_product_master = pd.DataFrame({"商品コード": ["P001"]})  # 在庫コスト等なし
        with pytest.raises(Exception):
            optimize(
                bad_product_master,
                pd.DataFrame({"項目": ["配送費_車両"], "数量": [5000]}),
                pd.DataFrame({
                    "商品コード": ["P001"],
                    "日付": [pd.Timestamp("2026-01-01")],
                    "入荷予定": [10],
                    "出荷予測": [10],
                    "出荷可能数累計": [10],
                }),
                pd.DataFrame({"商品コード": ["P001"], "前日末在庫": [0]}),
            )


# ---------------------------------------------------------------------------
# 要件 O-5: ベースライン計算関数
# ---------------------------------------------------------------------------

class TestO5_Baseline:
    """要件 O-5: ベースライン計算関数"""

    def test_O5_status_is_baseline(self, simple_baseline_result):
        """status が 'Baseline'"""
        assert simple_baseline_result["status"] == "Baseline"

    def test_O5_has_required_keys(self, simple_baseline_result):
        """返り値に必要なキーが全て含まれる"""
        assert set(simple_baseline_result.keys()) == {"status", "total_cost", "decision_variables", "trucks"}

    def test_O5_x_large_is_zero(self, simple_baseline_result):
        """大口入荷数は常に0"""
        assert (simple_baseline_result["decision_variables"]["大口入荷数"] == 0).all()

    def test_O5_n_trucks_is_zero(self, simple_baseline_result):
        """トラック台数は常に0"""
        assert (simple_baseline_result["trucks"]["トラック台数"] == 0).all()

    def test_O5_x_small_equals_x_bar(self, simple_baseline_result, simple_input_data):
        """小口入荷数 = 入荷予定"""
        dv = simple_baseline_result["decision_variables"]
        ts = simple_input_data["time_series"].set_index(["商品コード", "日付"])
        for _, row in dv.iterrows():
            expected = ts.loc[(row["商品コード"], row["日付"]), "入荷予定"]
            assert abs(row["小口入荷数"] - expected) < 0.01, \
                f"{row['商品コード']} {row['日付']}: expected {expected}, got {row['小口入荷数']}"

    def test_O5_inventory_transition(self, simple_baseline_result, simple_input_data):
        """在庫推移: I_{p,d} = I_{p,d-1} + x_small_{p,d} - s_{p,d}（負も許容）"""
        dv = simple_baseline_result["decision_variables"]
        ts = simple_input_data["time_series"].set_index(["商品コード", "日付"])
        inv_init = simple_input_data["inventory_init"].set_index("商品コード")

        for p in dv["商品コード"].unique():
            df_p = dv[dv["商品コード"] == p].sort_values("日付").reset_index(drop=True)
            for i, row in df_p.iterrows():
                d = row["日付"]
                s = ts.loc[(p, d), "出荷予測"]
                i_prev = inv_init.loc[p, "前日末在庫"] if i == 0 else df_p.loc[i - 1, "在庫"]
                expected = i_prev + row["小口入荷数"] - s
                assert abs(row["在庫"] - expected) < 0.01, \
                    f"{p} {d}: expected {expected}, got {row['在庫']}"

    def test_O5_total_cost_calculation(self, simple_baseline_result, simple_input_data):
        """total_cost = Σ(配送費_ケース × x_small) + Σ(在庫コスト × 在庫)"""
        dv = simple_baseline_result["decision_variables"]
        cost_per_case = simple_input_data["product_master"].set_index("商品コード")["配送費_ケース"]
        holding_cost = simple_input_data["product_master"].set_index("商品コード")["在庫コスト"]

        expected = sum(
            cost_per_case[row["商品コード"]] * row["小口入荷数"]
            + holding_cost[row["商品コード"]] * row["在庫"]
            for _, row in dv.iterrows()
        )
        assert abs(simple_baseline_result["total_cost"] - expected) < 0.01
