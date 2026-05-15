import pytest
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from charts import plot_order_and_inventory_all, plot_order_and_inventory_by_product


@pytest.fixture
def sample_dv():
    return pd.DataFrame({
        "日付": [pd.Timestamp("2024-01-01"), pd.Timestamp("2024-01-01"),
                 pd.Timestamp("2024-01-02"), pd.Timestamp("2024-01-02")],
        "商品コード": ["A", "B", "A", "B"],
        "小口入荷数": [10.0, 8.0, 5.0, 3.0],
        "大口入荷数": [0.0, 0.0, 0.0, 0.0],
        "入荷数合計": [10.0, 8.0, 5.0, 3.0],
        "在庫": [7.0, 5.0, 8.0, 6.0],
    })


# ── C-1: 全商品合計 入荷数・在庫推移 ──────────────────────────────


def test_C1_1_returns_figure(sample_dv):
    fig = plot_order_and_inventory_all(sample_dv)
    assert isinstance(fig, plt.Figure)
    plt.close(fig)


def test_C1_2_has_two_axes(sample_dv):
    fig = plot_order_and_inventory_all(sample_dv)
    assert len(fig.axes) == 2  # primary + twin
    plt.close(fig)


def test_C1_3_title(sample_dv):
    fig = plot_order_and_inventory_all(sample_dv)
    assert fig.axes[0].get_title() == "全商品合計 入荷数・在庫推移"
    plt.close(fig)


# ── C-2: 商品ごとの入荷数・在庫推移 ──────────────────────────────


def test_C2_1_returns_figure(sample_dv):
    fig = plot_order_and_inventory_by_product(sample_dv)
    assert isinstance(fig, plt.Figure)
    plt.close(fig)


def test_C2_2_subplot_count(sample_dv):
    fig = plot_order_and_inventory_by_product(sample_dv)
    n_products = sample_dv["商品コード"].nunique()
    assert len(fig.axes) == n_products * 2  # primary + twin per product
    plt.close(fig)


def test_C2_3_subplot_titles(sample_dv):
    fig = plot_order_and_inventory_by_product(sample_dv)
    products = sorted(sample_dv["商品コード"].unique())
    primary_axes = fig.axes[:len(products)]
    for ax, p in zip(primary_axes, products):
        assert p in ax.get_title()
    plt.close(fig)
