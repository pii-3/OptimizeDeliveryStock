import matplotlib.pyplot as plt


def plot_order_and_inventory_all(decision_variables_df):
    df = decision_variables_df.copy()
    daily = df.groupby("日付")[["小口入荷数", "大口入荷数", "在庫"]].sum().reset_index()
    daily = daily.sort_values("日付")

    fig, ax1 = plt.subplots(figsize=(10, 4))
    x = range(len(daily))

    ax1.bar(x, daily["小口入荷数"], 0.6, label="小口入荷数")
    ax1.bar(x, daily["大口入荷数"], 0.6, bottom=daily["小口入荷数"], label="大口入荷数")
    ax1.set_ylabel("入荷数（ケース）")
    ax1.set_xticks(list(x))
    ax1.set_xticklabels([d.strftime("%m/%d") for d in daily["日付"]])
    ax1.grid(axis="x")
    ax1.set_title("全商品合計 入荷数・在庫推移")

    ax2 = ax1.twinx()
    ax2.plot(list(x), daily["在庫"].tolist(), color="red", marker="o", label="在庫")
    ax2.set_ylabel("在庫（ケース）")

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

    for ax1, p in zip(axes, products):
        sub = df[df["商品コード"] == p].sort_values("日付")

        ax1.bar(list(x), sub["小口入荷数"].tolist(), label="小口入荷数")
        ax1.bar(list(x), sub["大口入荷数"].tolist(), bottom=sub["小口入荷数"].tolist(), label="大口入荷数")
        ax1.set_ylabel("入荷数（ケース）")
        ax1.set_xticks(list(x))
        ax1.set_xticklabels([d.strftime("%m/%d") for d in days])
        ax1.grid(axis="x")
        ax1.set_title(f"{p} 入荷数・在庫推移")

        ax2 = ax1.twinx()
        ax2.plot(list(x), sub["在庫"].tolist(), color="red", marker="o", label="在庫")
        ax2.set_ylabel("在庫（ケース）")

    fig.tight_layout()
    return fig
