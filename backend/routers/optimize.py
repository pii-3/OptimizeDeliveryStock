import io
import base64
import math

import matplotlib.pyplot as plt
import pandas as pd
from fastapi import APIRouter, HTTPException, UploadFile, File

from models.schemas import UploadResponse, ActionRequest, OptimizeResponse, CostBreakdown, SummaryKPIs
from services import session_store
from optimizer import load_excel, optimize, optimize_fixed_order, calculate_baseline
from charts import plot_order_and_inventory_all, plot_order_and_inventory_by_product

router = APIRouter()


def _fig_to_base64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100)
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def _df_to_records(df: pd.DataFrame) -> list[dict]:
    out = df.copy()
    for col in out.select_dtypes(include=["datetime64[ns]", "datetime64[ns, UTC]"]):
        out[col] = out[col].dt.strftime("%Y-%m-%d")
    for col in out.columns:
        if hasattr(out[col], "dt"):
            try:
                out[col] = out[col].dt.strftime("%Y-%m-%d")
            except Exception:
                pass
    return out.to_dict("records")


def _serialize_date_col(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "日付" in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out["日付"]):
            out["日付"] = out["日付"].dt.strftime("%Y-%m-%d")
        else:
            out["日付"] = out["日付"].astype(str)
    return out


def _build_response(result: dict, dfs: dict) -> OptimizeResponse:
    status = result["status"]

    if result["total_cost"] is None:
        return OptimizeResponse(status=status)

    cb = result.get("cost_breakdown")
    cost_breakdown = CostBreakdown(**cb) if cb else None

    dv: pd.DataFrame = result["decision_variables"].copy()
    trucks: pd.DataFrame = result["trucks"].copy()
    time_series_df: pd.DataFrame = dfs["time_series"]

    # KPI計算 (src/app.py:31-40 から移植)
    avg_inventory = dv.groupby("日付")["在庫"].sum().mean()
    avg_daily_shipment = time_series_df.groupby("日付")["出荷予測"].sum().mean()
    turnover_days = (
        avg_inventory / avg_daily_shipment
        if avg_daily_shipment > 0
        else float("nan")
    )
    if math.isnan(turnover_days):
        turnover_days = 0.0
    total_trucks = int(trucks["トラック台数"].sum())
    total_small = float(dv["小口入荷数"].sum())
    total_large = float(dv["大口入荷数"].sum())

    summary = SummaryKPIs(
        avg_inventory=float(avg_inventory),
        turnover_days=float(turnover_days),
        total_trucks=total_trucks,
        total_small_cases=total_small,
        total_large_cases=total_large,
    )

    # 日付を文字列に変換
    dv = _serialize_date_col(dv)
    trucks = _serialize_date_col(trucks)

    # 集計テーブル（C-1 の下に表示）
    agg = (
        dv.groupby("日付")[["小口入荷数", "大口入荷数", "在庫"]]
        .sum()
        .rename(columns={"小口入荷数": "小口入荷数（全商品）", "大口入荷数": "大口入荷数（全商品）", "在庫": "在庫（全商品）"})
        .reset_index()
    )

    # ピボットテーブル（C-2 の下に表示）
    pivot = dv.pivot_table(
        index="日付", columns="商品コード", values=["小口入荷数", "大口入荷数", "在庫"], aggfunc="sum"
    )
    pivot.columns = [f"{col[1]}_{col[0]}" for col in pivot.columns]
    pivot = pivot.reset_index()

    # グラフ生成
    fig1 = plot_order_and_inventory_all(result["decision_variables"])
    fig2 = plot_order_and_inventory_by_product(result["decision_variables"])
    chart_c1 = _fig_to_base64(fig1)
    chart_c2 = _fig_to_base64(fig2)

    # Excel生成
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        result["decision_variables"].to_excel(writer, sheet_name="入荷数・在庫", index=False)
        result["trucks"].to_excel(writer, sheet_name="トラック台数", index=False)
    excel_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    return OptimizeResponse(
        status=status,
        total_cost=result["total_cost"],
        cost_breakdown=cost_breakdown,
        summary=summary,
        decision_variables=_df_to_records(dv),
        trucks=_df_to_records(trucks),
        aggregated_by_date=_df_to_records(agg),
        pivot_by_date_product=_df_to_records(pivot),
        chart_c1_base64=chart_c1,
        chart_c2_base64=chart_c2,
        excel_base64=excel_b64,
    )


@router.post("/upload", response_model=UploadResponse)
async def upload(file: UploadFile = File(...)):
    if not file.filename.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="xlsx ファイルをアップロードしてください")
    content = await file.read()
    try:
        dfs = load_excel(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Excel の読み込みに失敗しました: {e}")
    session_store.clear_all()
    sid = session_store.new_session_id()
    session_store.save_session(sid, dfs)
    return UploadResponse(session_id=sid)


@router.post("/baseline", response_model=OptimizeResponse)
def run_baseline(req: ActionRequest):
    dfs = session_store.get_session(req.session_id)
    if dfs is None:
        raise HTTPException(status_code=404, detail="Session not found")
    result = calculate_baseline(
        dfs["product_master"], dfs["parameters"], dfs["time_series"], dfs["inventory_init"]
    )
    return _build_response(result, dfs)


@router.post("/fixed_order", response_model=OptimizeResponse)
def run_fixed_order(req: ActionRequest):
    dfs = session_store.get_session(req.session_id)
    if dfs is None:
        raise HTTPException(status_code=404, detail="Session not found")
    result = optimize_fixed_order(
        dfs["product_master"], dfs["parameters"], dfs["time_series"], dfs["inventory_init"]
    )
    return _build_response(result, dfs)


@router.post("/optimize", response_model=OptimizeResponse)
def run_optimize(req: ActionRequest):
    dfs = session_store.get_session(req.session_id)
    if dfs is None:
        raise HTTPException(status_code=404, detail="Session not found")
    result = optimize(
        dfs["product_master"], dfs["parameters"], dfs["time_series"], dfs["inventory_init"]
    )
    return _build_response(result, dfs)
