import pytest
import matplotlib.pyplot as plt
from pathlib import Path


class TestC1_InventoryAllChart:
    """要件 C-1: 全商品合計の在庫推移グラフ"""

    def test_C1_function_exists(self):
        """plot_inventory_all 関数が存在する"""
        try:
            from charts import plot_inventory_all
            assert callable(plot_inventory_all)
        except ImportError:
            pytest.skip("charts.py not implemented yet")

    def test_C1_returns_figure(self, sample_decision_variables):
        """関数が matplotlib Figure を返す"""
        from charts import plot_inventory_all
        fig = plot_inventory_all(sample_decision_variables)
        assert isinstance(fig, plt.Figure)

    def test_C1_figure_has_axes(self, sample_decision_variables):
        """Figure にスプロットが含まれる"""
        from charts import plot_inventory_all
        fig = plot_inventory_all(sample_decision_variables)
        assert len(fig.get_axes()) >= 1

    def test_C1_axes_has_line(self, sample_decision_variables):
        """Axes に Line2D が含まれる（折れ線グラフ）"""
        from charts import plot_inventory_all
        fig = plot_inventory_all(sample_decision_variables)
        ax = fig.get_axes()[0]
        lines = ax.get_lines()
        assert len(lines) >= 1


class TestC2_InventoryByProductChart:
    """要件 C-2: 商品ごとの在庫推移グラフ"""

    def test_C2_function_exists(self):
        """plot_inventory_by_product 関数が存在する"""
        try:
            from charts import plot_inventory_by_product
            assert callable(plot_inventory_by_product)
        except ImportError:
            pytest.skip("charts.py not implemented yet")

    def test_C2_returns_figure(self, sample_decision_variables):
        """関数が matplotlib Figure を返す"""
        from charts import plot_inventory_by_product
        fig = plot_inventory_by_product(sample_decision_variables)
        assert isinstance(fig, plt.Figure)

    def test_C2_has_multiple_subplots(self, sample_decision_variables):
        """商品数分のサブプロットがある"""
        from charts import plot_inventory_by_product
        fig = plot_inventory_by_product(sample_decision_variables)
        num_products = sample_decision_variables["商品コード"].nunique()
        assert len(fig.get_axes()) == num_products

    def test_C2_each_subplot_has_line(self, sample_decision_variables):
        """各サブプロットに折れ線グラフがある"""
        from charts import plot_inventory_by_product
        fig = plot_inventory_by_product(sample_decision_variables)
        for ax in fig.get_axes():
            lines = ax.get_lines()
            assert len(lines) >= 1


class TestC3_OrderAndInventoryChart:
    """要件 C-3: 商品ごとの入荷数・在庫推移グラフ"""

    def test_C3_function_exists(self):
        """plot_order_and_inventory_by_product 関数が存在する"""
        try:
            from charts import plot_order_and_inventory_by_product
            assert callable(plot_order_and_inventory_by_product)
        except ImportError:
            pytest.skip("charts.py not implemented yet")

    def test_C3_returns_figure(self, sample_decision_variables):
        """関数が matplotlib Figure を返す"""
        from charts import plot_order_and_inventory_by_product
        fig = plot_order_and_inventory_by_product(sample_decision_variables)
        assert isinstance(fig, plt.Figure)

    def test_C3_has_multiple_subplots(self, sample_decision_variables):
        """商品数分のサブプロットがある（主軸と副軸で2倍）"""
        from charts import plot_order_and_inventory_by_product
        fig = plot_order_and_inventory_by_product(sample_decision_variables)
        num_products = sample_decision_variables["商品コード"].nunique()
        # 主軸 + 副軸(twinx) で 2倍になる
        assert len(fig.get_axes()) == num_products * 2

    def test_C3_each_subplot_has_bar_and_line(self, sample_decision_variables):
        """各サブプロットに棒グラフと折れ線グラフがある"""
        from charts import plot_order_and_inventory_by_product
        fig = plot_order_and_inventory_by_product(sample_decision_variables)
        num_products = sample_decision_variables["商品コード"].nunique()

        # matplotlib は主軸を先に、副軸を後に返す
        # [ax1, ax2, ax3, ax2_1, ax2_2, ax2_3]
        primary_axes = fig.get_axes()[:num_products]
        secondary_axes = fig.get_axes()[num_products:]

        # 各主軸に棒グラフがある
        for ax in primary_axes:
            patches = ax.patches
            assert len(patches) > 0, "No bar chart found"

        # 各副軸に折れ線グラフがある
        for ax in secondary_axes:
            lines = ax.get_lines()
            assert len(lines) > 0, "No line chart found"
