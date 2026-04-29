import pytest
import matplotlib.pyplot as plt
from pathlib import Path


class TestC1_OrderAndInventoryAllChart:
    """要件 C-1: 全商品合計の入荷数・在庫推移グラフ"""

    def test_C1_function_exists(self):
        """plot_order_and_inventory_all 関数が存在する"""
        from charts import plot_order_and_inventory_all
        assert callable(plot_order_and_inventory_all)

    def test_C1_returns_figure(self, sample_decision_variables):
        """関数が matplotlib Figure を返す"""
        from charts import plot_order_and_inventory_all
        fig = plot_order_and_inventory_all(sample_decision_variables)
        assert isinstance(fig, plt.Figure)

    def test_C1_has_two_axes(self, sample_decision_variables):
        """主軸と副軸(twinx)の2軸がある"""
        from charts import plot_order_and_inventory_all
        fig = plot_order_and_inventory_all(sample_decision_variables)
        assert len(fig.get_axes()) == 2

    def test_C1_primary_axis_has_bars(self, sample_decision_variables):
        """主軸に棒グラフ（入荷数）がある"""
        from charts import plot_order_and_inventory_all
        fig = plot_order_and_inventory_all(sample_decision_variables)
        ax = fig.get_axes()[0]
        assert len(ax.patches) > 0

    def test_C1_secondary_axis_has_line(self, sample_decision_variables):
        """副軸に折れ線グラフ（在庫）がある"""
        from charts import plot_order_and_inventory_all
        fig = plot_order_and_inventory_all(sample_decision_variables)
        ax2 = fig.get_axes()[1]
        assert len(ax2.get_lines()) > 0


class TestC2_OrderAndInventoryByProductChart:
    """要件 C-2: 商品ごとの入荷数・在庫推移グラフ"""

    def test_C2_function_exists(self):
        """plot_order_and_inventory_by_product 関数が存在する"""
        from charts import plot_order_and_inventory_by_product
        assert callable(plot_order_and_inventory_by_product)

    def test_C2_returns_figure(self, sample_decision_variables):
        """関数が matplotlib Figure を返す"""
        from charts import plot_order_and_inventory_by_product
        fig = plot_order_and_inventory_by_product(sample_decision_variables)
        assert isinstance(fig, plt.Figure)

    def test_C2_has_multiple_subplots(self, sample_decision_variables):
        """商品数分のサブプロットがある（主軸と副軸で2倍）"""
        from charts import plot_order_and_inventory_by_product
        fig = plot_order_and_inventory_by_product(sample_decision_variables)
        num_products = sample_decision_variables["商品コード"].nunique()
        assert len(fig.get_axes()) == num_products * 2

    def test_C2_each_subplot_has_bar_and_line(self, sample_decision_variables):
        """各サブプロットに棒グラフと折れ線グラフがある"""
        from charts import plot_order_and_inventory_by_product
        fig = plot_order_and_inventory_by_product(sample_decision_variables)
        num_products = sample_decision_variables["商品コード"].nunique()

        primary_axes = fig.get_axes()[:num_products]
        secondary_axes = fig.get_axes()[num_products:]

        for ax in primary_axes:
            assert len(ax.patches) > 0, "No bar chart found"
        for ax in secondary_axes:
            assert len(ax.get_lines()) > 0, "No line chart found"
