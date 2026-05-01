function MetricCard({ label, value }) {
  return (
    <div className="metric-card">
      <div className="label">{label}</div>
      <div className="value">{value}</div>
    </div>
  );
}

export default function CostMetrics({ totalCost, costBreakdown }) {
  const fmt = (n) => `¥${Math.round(n).toLocaleString("ja-JP")}`;

  return (
    <div>
      <p style={{ marginBottom: 12 }}>
        総コスト: <strong>{fmt(totalCost)}</strong>
      </p>
      {costBreakdown && (
        <div className="metrics-row">
          <MetricCard label="配送コスト（小口）" value={fmt(costBreakdown.delivery_small)} />
          <MetricCard label="配送コスト（大口）" value={fmt(costBreakdown.delivery_large)} />
          <MetricCard label="在庫コスト" value={fmt(costBreakdown.holding)} />
        </div>
      )}
    </div>
  );
}
