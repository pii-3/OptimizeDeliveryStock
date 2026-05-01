import CostMetrics from "./CostMetrics";
import SummaryMetrics from "./SummaryMetrics";
import DataTable from "./DataTable";
import ChartSection from "./ChartSection";
import ExcelDownload from "./ExcelDownload";

function StatusBadge({ status }) {
  const cls =
    status === "Optimal" ? "optimal" : status === "Baseline" ? "baseline" : "error";
  return <span className={`status-badge ${cls}`}>{status}</span>;
}

export default function ResultsPanel({ result, filePrefix = "result" }) {
  if (!result) return null;

  return (
    <div>
      <h2>結果</h2>
      <StatusBadge status={result.status} />

      {result.total_cost == null ? (
        <div className="error-box">
          最適解が見つかりませんでした。入力データを確認してください。
        </div>
      ) : (
        <>
          <div className="card">
            <CostMetrics
              totalCost={result.total_cost}
              costBreakdown={result.cost_breakdown}
            />
            <SummaryMetrics summary={result.summary} />
          </div>

          <h2>入荷数・在庫</h2>
          <div className="card">
            <DataTable data={result.decision_variables} />
          </div>

          <h2>トラック台数</h2>
          <div className="card">
            <DataTable data={result.trucks} />
          </div>

          <h2>グラフ</h2>
          <div className="card">
            <ChartSection
              title="全商品合計 入荷数・在庫推移 (C-1)"
              base64={result.chart_c1_base64}
              downloadFilename={`${filePrefix}_order_and_inventory_all.png`}
              tableData={result.aggregated_by_date}
            />
          </div>

          <div className="card">
            <ChartSection
              title="商品ごとの入荷数・在庫推移 (C-2)"
              base64={result.chart_c2_base64}
              downloadFilename={`${filePrefix}_order_and_inventory_by_product.png`}
              tableData={result.pivot_by_date_product}
            />
          </div>

          <ExcelDownload
            base64={result.excel_base64}
            filename={`${filePrefix}.xlsx`}
          />
        </>
      )}
    </div>
  );
}
