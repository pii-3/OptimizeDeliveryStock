import matplotlib.pyplot as plt
import matplotlib

matplotlib.rcParams["font.family"] = "Yu Gothic"


def plot_order_and_inventory_all(decision_variables_df):
    df = decision_variables_df.copy()
    daily = df.groupby("日付")[["小口入荷数", "大口入荷数", "在庫"]].sum().reset_index()
    daily = daily.sort_values("日付")

    fig, ax = plt.subplots(figsize=(10, 4))
    x = range(len(daily))

    ax.bar(x, daily["小口入荷数"], 0.6, label="小口入荷数")
    ax.bar(x, daily["大口入荷数"], 0.6, bottom=daily["小口入荷数"], label="大口入荷数")
    ax.plot(list(x), daily["在庫"].tolist(), color="red", marker="o", label="在庫")
    ax.set_ylabel("ケース数")
    ax.set_xticks(list(x))
    ax.set_xticklabels([d.strftime("%m/%d") for d in daily["日付"]])
    ax.grid(axis="x")
    ax.set_title("全商品合計 入荷数・在庫推移")
    ax.legend(loc="upper left")

    return fig


def plot_order_and_inventory_by_product(decision_variables_df):
    df = decision_variables_df.copy()
    products = sorted(df["商品コード"].unique())
    n = len(products)
    days = sorted(df["日付"].unique())
    x = range(len(days))

    fig, axes = plt.subplots(n, 1, figsize=(10, 4 * n))
    if n == 1:
        axes = [axes]

    for ax, p in zip(axes, products):
        sub = df[df["商品コード"] == p].sort_values("日付")

        ax.bar(list(x), sub["小口入荷数"].tolist(), label="小口入荷数")
        ax.bar(list(x), sub["大口入荷数"].tolist(), bottom=sub["小口入荷数"].tolist(), label="大口入荷数")
        ax.plot(list(x), sub["在庫"].tolist(), color="red", marker="o", label="在庫")
        ax.set_ylabel("ケース数")
        ax.set_xticks(list(x))
        ax.set_xticklabels([d.strftime("%m/%d") for d in days])
        ax.grid(axis="x")
        ax.set_title(f"{p} 入荷数・在庫推移")
        ax.legend(loc="upper left")

    fig.tight_layout()
    return fig
