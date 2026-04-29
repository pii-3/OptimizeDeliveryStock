import io
import pandas as pd
import streamlit as st
from optimizer import load_excel, optimize, calculate_baseline
from charts import (
    plot_order_and_inventory_all,
    plot_order_and_inventory_by_product,
)


def _display_result(result, time_series_df, file_prefix="result"):
    st.subheader("結果")
    st.write(f"ステータス: **{result['status']}**")

    if result["total_cost"] is None:
        st.error("最適解が見つかりませんでした。入力データを確認してください。")
        return

    st.write(f"総コスト: **¥{result['total_cost']:,.0f}**")

    cb = result.get("cost_breakdown")
    if cb is not None:
        c1, c2, c3 = st.columns(3)
        c1.metric("配送コスト（小口）", f"¥{cb['delivery_small']:,.0f}")
        c2.metric("配送コスト（大口）", f"¥{cb['delivery_large']:,.0f}")
        c3.metric("在庫コスト", f"¥{cb['holding']:,.0f}")

    dv = result["decision_variables"]
    trucks = result["trucks"]

    avg_inventory = dv.groupby("日付")["在庫"].sum().mean()
    avg_daily_shipment = time_series_df.groupby("日付")["出荷予測"].sum().mean()
    turnover_days = (
        avg_inventory / avg_daily_shipment
        if avg_daily_shipment > 0
        else float("nan")
    )
    total_trucks = int(trucks["トラック台数"].sum())
    total_small = dv["小口入荷数"].sum()
    total_large = dv["大口入荷数"].sum()

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("平均在庫（ケース）", f"{avg_inventory:,.1f}")
    col2.metric("回転日数", f"{turnover_days:.1f} 日")
    col3.metric("大口トラック台数（合計）", f"{total_trucks:,} 台")
    col4.metric("小口ケース数（合計）", f"{total_small:,.0f}")
    col5.metric("大口ケース数（合計）", f"{total_large:,.0f}")

    st.subheader("入荷数・在庫")
    st.dataframe(dv, use_container_width=True)

    st.subheader("トラック台数")
    st.dataframe(trucks, use_container_width=True)

    st.subheader("グラフ")

    st.markdown("#### 全商品合計 入荷数・在庫推移 (C-1)")
    fig1 = plot_order_and_inventory_all(dv)
    st.pyplot(fig1)
    buf1 = io.BytesIO()
    fig1.savefig(buf1, format="png", dpi=100)
    st.download_button("PNG ダウンロード", buf1.getvalue(), f"{file_prefix}_order_and_inventory_all.png", "image/png")
    tbl1 = (
        dv.groupby("日付")[["小口入荷数", "大口入荷数", "在庫"]]
        .sum()
        .rename(columns={"小口入荷数": "小口入荷数（全商品）", "大口入荷数": "大口入荷数（全商品）", "在庫": "在庫（全商品）"})
        .reset_index()
    )
    st.dataframe(tbl1, use_container_width=True)

    st.markdown("#### 商品ごとの入荷数・在庫推移 (C-2)")
    fig2 = plot_order_and_inventory_by_product(dv)
    st.pyplot(fig2)
    buf2 = io.BytesIO()
    fig2.savefig(buf2, format="png", dpi=100)
    st.download_button("PNG ダウンロード", buf2.getvalue(), f"{file_prefix}_order_and_inventory_by_product.png", "image/png")
    tbl2 = dv.pivot_table(
        index="日付", columns="商品コード", values=["小口入荷数", "大口入荷数", "在庫"]
    )
    tbl2.columns = [f"{col[1]}_{col[0]}" for col in tbl2.columns]
    tbl2 = tbl2.reset_index()
    st.dataframe(tbl2, use_container_width=True)

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        dv.to_excel(writer, sheet_name="入荷数・在庫", index=False)
        trucks.to_excel(writer, sheet_name="トラック台数", index=False)
    st.download_button(
        label="結果をExcelでダウンロード",
        data=buffer.getvalue(),
        file_name=f"{file_prefix}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


st.title("入荷最適化")

uploaded_file = st.file_uploader("Excelファイルをアップロード", type=["xlsx"])

if uploaded_file is not None:
    dfs = load_excel(uploaded_file)

    col_baseline, col_optimize = st.columns(2)
    btn_baseline = col_baseline.button("インプットデータで確認")
    btn_optimize = col_optimize.button("最適化を実行")

    if btn_baseline:
        with st.spinner("計算中..."):
            result = calculate_baseline(
                dfs["product_master"],
                dfs["parameters"],
                dfs["time_series"],
                dfs["inventory_init"],
            )
        _display_result(result, dfs["time_series"], file_prefix="baseline_result")

    if btn_optimize:
        with st.spinner("計算中..."):
            result = optimize(
                dfs["product_master"],
                dfs["parameters"],
                dfs["time_series"],
                dfs["inventory_init"],
            )
        _display_result(result, dfs["time_series"], file_prefix="optimization_result")
