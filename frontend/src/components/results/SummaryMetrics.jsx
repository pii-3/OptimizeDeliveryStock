function MetricCard({ label, value }) {
  return (
    <div className="metric-card">
      <div className="label">{label}</div>
      <div className="value">{value}</div>
    </div>
  );
}

export default function SummaryMetrics({ summary }) {
  if (!summary) return null;
  return (
    <div className="metrics-row">
      <MetricCard
        label="平均在庫（ケース）"
        value={summary.avg_inventory.toLocaleString("ja-JP", { maximumFractionDigits: 1 })}
      />
      <MetricCard
        label="回転日数"
        value={`${summary.turnover_days.toFixed(1)} 日`}
      />
      <MetricCard
        label="大口トラック台数（合計）"
        value={`${summary.total_trucks.toLocaleString("ja-JP")} 台`}
      />
      <MetricCard
        label="小口ケース数（合計）"
        value={Math.round(summary.total_small_cases).toLocaleString("ja-JP")}
      />
      <MetricCard
        label="大口ケース数（合計）"
        value={Math.round(summary.total_large_cases).toLocaleString("ja-JP")}
      />
    </div>
  );
}
