import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd

# Windows で日本語フォントが豆腐になるのを防ぐ
matplotlib.rcParams["font.family"] = ["Yu Gothic", "MS Gothic", "Meiryo", "sans-serif"]
matplotlib.rcParams["axes.unicode_minus"] = False


def plot_inventory_all(df: pd.DataFrame) -> plt.Figure:
    """
    要件 C-1: 全商品合計の在庫推移グラフ

    Args:
        df: decision_variables DataFrame

    Returns:
        matplotlib Figure オブジェクト
    """
    inventory_total = df.groupby("日付")["在庫"].sum()

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(inventory_total.index, inventory_total.values, marker="o", linewidth=2)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
    ax.set_xlabel("日付")
    ax.set_ylabel("在庫数")
    ax.set_title("全商品合計 在庫推移")
    ax.grid(True)
    fig.autofmt_xdate()
    plt.tight_layout()

    return fig


def plot_order_and_inventory_all(df: pd.DataFrame) -> plt.Figure:
    """
    要件 C-4: 全商品合計の入荷数・在庫推移グラフ

    Args:
        df: decision_variables DataFrame

    Returns:
        matplotlib Figure オブジェクト
    """
    total = df.groupby("日付")[["小口入荷数", "大口入荷数", "在庫"]].sum().sort_index()

    fig, ax = plt.subplots(figsize=(10, 4))

    ax.bar(total.index, total["小口入荷数"], label="小口入荷", alpha=0.7)
    ax.bar(total.index, total["大口入荷数"], bottom=total["小口入荷数"], label="大口入荷", alpha=0.7)
    ax.set_ylabel("入荷数")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
    ax.set_title("全商品合計 入荷数・在庫推移")
    ax.grid(True, axis="x")

    ax2 = ax.twinx()
    ax2.plot(total.index, total["在庫"], marker="o", color="tab:red", linewidth=2, label="在庫")
    ax2.set_ylabel("在庫数")

    y_max = max((total["小口入荷数"] + total["大口入荷数"]).max(), total["在庫"].max()) * 1.1
    ax.set_ylim(0, y_max)
    ax2.set_ylim(0, y_max)

    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, loc="upper left")

    fig.autofmt_xdate()
    plt.tight_layout()

    return fig


def plot_inventory_by_product(df: pd.DataFrame) -> plt.Figure:
    """
    要件 C-2: 商品ごとの在庫推移グラフ

    Args:
        df: decision_variables DataFrame

    Returns:
        matplotlib Figure オブジェクト（複数サブプロット）
    """
    products = sorted(df["商品コード"].unique())
    n = len(products)

    fig, axes = plt.subplots(n, 1, figsize=(10, 4 * n), sharex=True)
    if n == 1:
        axes = [axes]

    for ax, product in zip(axes, products):
        subset = df[df["商品コード"] == product].set_index("日付").sort_index()
        ax.plot(subset.index, subset["在庫"], marker="o", linewidth=2)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
        ax.set_ylabel("在庫数")
        ax.set_title(f"{product} 在庫推移")
        ax.grid(True)

    fig.autofmt_xdate()
    plt.tight_layout()

    return fig


def plot_order_and_inventory_by_product(df: pd.DataFrame) -> plt.Figure:
    """
    要件 C-3: 商品ごとの入荷数・在庫推移グラフ

    Args:
        df: decision_variables DataFrame

    Returns:
        matplotlib Figure オブジェクト（複数サブプロット）
    """
    products = sorted(df["商品コード"].unique())
    n = len(products)

    fig, axes = plt.subplots(n, 1, figsize=(10, 4 * n), sharex=True)
    if n == 1:
        axes = [axes]

    for ax, product in zip(axes, products):
        subset = df[df["商品コード"] == product].set_index("日付").sort_index()

        # 主軸: 入荷数（棒グラフ、積み上げ）
        ax.bar(subset.index, subset["小口入荷数"], label="小口入荷", alpha=0.7)
        ax.bar(
            subset.index,
            subset["大口入荷数"],
            bottom=subset["小口入荷数"],
            label="大口入荷",
            alpha=0.7,
        )
        ax.set_ylabel("入荷数")
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
        ax.set_title(f"{product} 入荷数・在庫推移")
        ax.grid(True, axis="x")

        # 副軸: 在庫（折れ線）
        ax2 = ax.twinx()
        ax2.plot(
            subset.index, subset["在庫"], marker="o", color="tab:red", linewidth=2, label="在庫"
        )
        ax2.set_ylabel("在庫数")

        y_max = max((subset["小口入荷数"] + subset["大口入荷数"]).max(), subset["在庫"].max()) * 1.1
        ax.set_ylim(0, y_max)
        ax2.set_ylim(0, y_max)

        # 凡例を統合
        lines1, labels1 = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(lines1 + lines2, labels1 + labels2, loc="upper left")

    fig.autofmt_xdate()
    plt.tight_layout()

    return fig
