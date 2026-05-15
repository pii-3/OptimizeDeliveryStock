import io
import streamlit as st
import pandas as pd
from optimizer import load_excel, optimize, calculate_baseline, optimize_fixed_order
from charts import plot_order_and_inventory_all, plot_order_and_inventory_by_product


def _fmt_yen(value):
    return f"¥{int(value):,}"


def _show_result(result, time_series_df):
    if result["status"] not in ("Optimal", "Baseline"):
        st.error("最適解が見つかりませんでした。入力データを確認してください。")
        return

    st.markdown(f"**ステータス: {result['status']}**")

    if result["total_cost"] is None:
        return

    st.metric("総コスト", _fmt_yen(result["total_cost"]))

    # コスト内訳（3列）
    breakdown = result["cost_breakdown"]
    c1, c2, c3 = st.columns(3)
    c1.metric("配送コスト（小口）", _fmt_yen(breakdown["delivery_small"]))
    c2.metric("配送コスト（大口）", _fmt_yen(breakdown["delivery_large"]))
    c3.metric("在庫コスト", _fmt_yen(breakdown["holding"]))

    # サマリーメトリクス（5列）
    dv = result["decision_variables"]
    trucks = result["trucks"]

    avg_inv = dv.groupby("日付")["在庫"].sum().mean()
    avg_daily_shipping = time_series_df.groupby("日付")["出荷予測"].sum().mean()
    turnover_days = avg_inv / avg_daily_shipping if avg_daily_shipping > 0 else 0.0

    s1, s2, s3, s4, s5 = st.columns(5)
    s1.metric("平均在庫（ケース）", f"{avg_inv:.1f}")
    s2.metric("回転日数", f"{turnover_days:.1f}")
    s3.metric("大口トラック台数（合計）", f"{int(trucks['トラック台数'].sum())}")
    s4.metric("小口ケース数（合計）", f"{int(dv['小口入荷数'].sum())}")
    s5.metric("大口ケース数（合計）", f"{int(dv['大口入荷数'].sum())}")

    # テーブル
    st.subheader("入荷数・在庫")
    st.dataframe(dv)

    st.subheader("トラック台数")
    st.dataframe(trucks)

    # グラフ
    fig1 = plot_order_and_inventory_all(dv)
    st.pyplot(fig1)

    fig2 = plot_order_and_inventory_by_product(dv)
    st.pyplot(fig2)

    # Excel ダウンロード
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        dv.to_excel(writer, sheet_name="入荷数・在庫", index=False)
        trucks.to_excel(writer, sheet_name="トラック台数", index=False)
    st.download_button(
        "結果をExcelでダウンロード",
        buf.getvalue(),
        file_name="optimization_result.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# ── メイン ──────────────────────────────────────────────────────

st.title("入荷最適化")

uploaded_file = st.file_uploader("Excelファイルをアップロード", type=["xlsx"])

if uploaded_file is not None:
    try:
        dfs = load_excel(uploaded_file)
    except ValueError as e:
        st.error(str(e))
        st.stop()
    except Exception as e:
        st.error(f"ファイルの読み込みに失敗しました: {e}")
        st.stop()

    col1, col2, col3 = st.columns(3)
    run_baseline = col1.button("すべて小口で配送")
    run_fixed = col2.button("日付・商品ごとの発注数は固定で最適化")
    run_optimize = col3.button("最適化を実行")

    if run_baseline:
        with st.spinner("計算中..."):
            try:
                st.session_state["result"] = calculate_baseline(
                    dfs["product_master"], dfs["parameters"],
                    dfs["time_series"], dfs["inventory_init"],
                )
                st.session_state["time_series"] = dfs["time_series"]
            except Exception as e:
                st.error(str(e))

    if run_fixed:
        with st.spinner("計算中..."):
            try:
                st.session_state["result"] = optimize_fixed_order(
                    dfs["product_master"], dfs["parameters"],
                    dfs["time_series"], dfs["inventory_init"],
                )
                st.session_state["time_series"] = dfs["time_series"]
            except Exception as e:
                st.error(str(e))

    if run_optimize:
        with st.spinner("計算中..."):
            try:
                st.session_state["result"] = optimize(
                    dfs["product_master"], dfs["parameters"],
                    dfs["time_series"], dfs["inventory_init"],
                )
                st.session_state["time_series"] = dfs["time_series"]
            except Exception as e:
                st.error(str(e))

if "result" in st.session_state:
    st.divider()
    _show_result(st.session_state["result"], st.session_state["time_series"])
