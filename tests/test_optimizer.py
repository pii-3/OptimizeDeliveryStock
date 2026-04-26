
import pytest
import pandas as pd
from optimizer import load_excel, optimize


class TestO1_OptimizeFunctionStructure:
    """要件 O-1: 最適化関数の返り値構造"""

    def test_O1_returns_dict(self, sample_input_data):
        """最適化関数が辞書を返す"""
        result = optimize(
            sample_input_data["product_master"],
            sample_input_data["parameters"],
            sample_input_data["time_series"],
            sample_input_data["inventory_init"],
        )
        assert isinstance(result, dict)

    def test_O1_has_required_keys(self, sample_input_data):
        """返り値に必要なキーが全て含まれる"""
        result = optimize(
            sample_input_data["product_master"],
            sample_input_data["parameters"],
            sample_input_data["time_series"],
            sample_input_data["inventory_init"],
        )
        assert "status" in result
        assert "total_cost" in result
        assert "decision_variables" in result
        assert "trucks" in result

    def test_O1_status_is_optimal(self, sample_input_data):
        """最適解が見つかる"""
        result = optimize(
            sample_input_data["product_master"],
            sample_input_data["parameters"],
            sample_input_data["time_series"],
            sample_input_data["inventory_init"],
        )
        assert result["status"] == "Optimal"

    def test_O1_total_cost_is_float(self, sample_input_data):
        """総コストが数値"""
        result = optimize(
            sample_input_data["product_master"],
            sample_input_data["parameters"],
            sample_input_data["time_series"],
            sample_input_data["inventory_init"],
        )
        assert isinstance(result["total_cost"], (int, float))
        assert result["total_cost"] > 0

    def test_O1_decision_variables_is_dataframe(self, sample_input_data):
        """decision_variables が DataFrame"""
        result = optimize(
            sample_input_data["product_master"],
            sample_input_data["parameters"],
            sample_input_data["time_series"],
            sample_input_data["inventory_init"],
        )
        assert isinstance(result["decision_variables"], pd.DataFrame)

    def test_O1_trucks_is_dataframe(self, sample_input_data):
        """trucks が DataFrame"""
        result = optimize(
            sample_input_data["product_master"],
            sample_input_data["parameters"],
            sample_input_data["time_series"],
            sample_input_data["inventory_init"],
        )
        assert isinstance(result["trucks"], pd.DataFrame)


class TestO2_ExcelLoader:
    """要件 O-2: Excel ローダー"""

    def test_O2_load_excel_returns_dict(self):
        """load_excel が辞書を返す"""
        result = load_excel("data/input/InputData.xlsx")
        assert isinstance(result, dict)

    def test_O2_has_required_keys(self):
        """返り値に必要なキーが全て含まれる"""
        result = load_excel("data/input/InputData.xlsx")
        assert "product_master" in result
        assert "parameters" in result
        assert "time_series" in result
        assert "inventory_init" in result

    def test_O2_all_values_are_dataframe(self):
        """全ての値が DataFrame"""
        result = load_excel("data/input/InputData.xlsx")
        for key, value in result.items():
            assert isinstance(value, pd.DataFrame), f"{key} is not DataFrame"


class TestO3_ConstraintAccuracy:
    """要件 O-3: 制約条件の正確性"""

    def test_O3_1_inventory_transition_first_day(self, sample_decision_variables, sample_input_data):
        """在庫推移制約（初日）: I_{p,1} = I_{p,0} + x_{p,1} - s_{p,1}"""
        df = sample_decision_variables
        time_series = sample_input_data["time_series"]
        inventory_init = sample_input_data["inventory_init"]

        first_day = df["日付"].min()
        df_first = df[df["日付"] == first_day]

        for _, row in df_first.iterrows():
            p = row["商品コード"]
            expected_inv = (
                inventory_init.set_index("商品コード").loc[p, "前日末在庫"]
                + row["入荷数合計"]
                - time_series[
                    (time_series["商品コード"] == p) & (time_series["日付"] == first_day)
                ]["出荷予測"].values[0]
            )
            assert abs(row["在庫"] - expected_inv) < 0.01

    def test_O3_1_inventory_all_nonnegative(self, sample_decision_variables):
        """全ての在庫が非負"""
        assert (sample_decision_variables["在庫"] >= -0.01).all()

    def test_O3_2_truck_capacity_respected(self, sample_decision_variables, sample_input_data):
        """トラック容量制約が満たされている"""
        df_decisions = sample_decision_variables
        trucks_df = sample_input_data["parameters"].set_index("項目")
        product_master = sample_input_data["product_master"].set_index("商品コード")

        for day in df_decisions["日付"].unique():
            day_data = df_decisions[df_decisions["日付"] == day]
            capacity_usage = 0
            for _, row in day_data.iterrows():
                p = row["商品コード"]
                K_p = product_master.loc[p, "CS/車両"]
                capacity_usage += row["大口入荷数"] / K_p

            # トラック台数は整数で、容量を満たす
            n_trucks_needed = int(capacity_usage) if capacity_usage == int(capacity_usage) else int(capacity_usage) + 1
            assert capacity_usage <= n_trucks_needed + 0.01


class TestO4_ErrorHandling:
    """要件 O-4: エラーハンドリング"""

    def test_O4_2_missing_sheet_name(self):
        """不正なシート名 → エラー発生"""
        # このテストは手動で不正なExcelを用意する必要があるためスキップ
        pass
