import io
import pandas as pd
import streamlit as st
from optimizer import load_excel, optimize
from charts import (
    plot_inventory_all,
    plot_order_and_inventory_all,
    plot_inventory_by_product,
    plot_order_and_inventory_by_product,
)

st.title("入荷最適化")

uploaded_file = st.file_uploader("Excelファイルをアップロード", type=["xlsx"])

if uploaded_file is not None:
    dfs = load_excel(uploaded_file)

    if st.button("最適化を実行"):
        with st.spinner("計算中..."):
            result = optimize(
                dfs["product_master"],
                dfs["parameters"],
                dfs["time_series"],
                dfs["inventory_init"],
            )

        st.subheader("結果")
        st.write(f"ステータス: **{result['status']}**")

        if result["total_cost"] is not None:
            st.write(f"総コスト: **{result['total_cost']:,.0f}**")

            dv = result["decision_variables"]
            trucks = result["trucks"]

            avg_inventory = dv.groupby("日付")["在庫"].sum().mean()
            avg_daily_shipment = (
                dfs["time_series"].groupby("日付")["出荷予測"].sum().mean()
            )
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
            st.dataframe(result["decision_variables"], use_container_width=True)

            st.subheader("トラック台数")
            st.dataframe(result["trucks"], use_container_width=True)

            # グラフ表示
            st.subheader("グラフ")

            st.markdown("#### 全商品合計 在庫推移 (C-1)")
            fig1 = plot_inventory_all(dv)
            st.pyplot(fig1)
            buf1 = io.BytesIO()
            fig1.savefig(buf1, format="png", dpi=100)
            st.download_button("PNG ダウンロード", buf1.getvalue(), "inventory_all.png", "image/png")
            tbl1 = (
                dv.groupby("日付")[["入荷数合計", "在庫"]]
                .sum()
                .rename(columns={"入荷数合計": "入荷数合計（全商品）", "在庫": "在庫（全商品）"})
                .reset_index()
            )
            st.dataframe(tbl1, use_container_width=True)

            st.markdown("#### 全商品合計 入荷数・在庫推移 (C-4)")
            fig4 = plot_order_and_inventory_all(dv)
            st.pyplot(fig4)
            buf4 = io.BytesIO()
            fig4.savefig(buf4, format="png", dpi=100)
            st.download_button("PNG ダウンロード", buf4.getvalue(), "order_and_inventory_all.png", "image/png")
            tbl4 = (
                dv.groupby("日付")[["小口入荷数", "大口入荷数", "在庫"]]
                .sum()
                .rename(columns={"小口入荷数": "小口入荷数（全商品）", "大口入荷数": "大口入荷数（全商品）", "在庫": "在庫（全商品）"})
                .reset_index()
            )
            st.dataframe(tbl4, use_container_width=True)

            st.markdown("#### 商品ごとの在庫推移 (C-2)")
            fig2 = plot_inventory_by_product(dv)
            st.pyplot(fig2)
            buf2 = io.BytesIO()
            fig2.savefig(buf2, format="png", dpi=100)
            st.download_button("PNG ダウンロード", buf2.getvalue(), "inventory_by_product.png", "image/png")
            tbl2 = dv.pivot_table(index="日付", columns="商品コード", values="在庫").reset_index()
            tbl2.columns.name = None
            st.dataframe(tbl2, use_container_width=True)

            st.markdown("#### 商品ごとの入荷数・在庫推移 (C-3)")
            fig3 = plot_order_and_inventory_by_product(dv)
            st.pyplot(fig3)
            buf3 = io.BytesIO()
            fig3.savefig(buf3, format="png", dpi=100)
            st.download_button("PNG ダウンロード", buf3.getvalue(), "order_and_inventory.png", "image/png")
            tbl3 = dv.pivot_table(
                index="日付", columns="商品コード", values=["小口入荷数", "大口入荷数", "在庫"]
            )
            tbl3.columns = [f"{col[1]}_{col[0]}" for col in tbl3.columns]
            tbl3 = tbl3.reset_index()
            st.dataframe(tbl3, use_container_width=True)

            # Excelダウンロード
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                result["decision_variables"].to_excel(writer, sheet_name="入荷数・在庫", index=False)
                result["trucks"].to_excel(writer, sheet_name="トラック台数", index=False)
            st.download_button(
                label="結果をExcelでダウンロード",
                data=buffer.getvalue(),
                file_name="optimization_result.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        else:
            st.error("最適解が見つかりませんでした。入力データを確認してください。")
