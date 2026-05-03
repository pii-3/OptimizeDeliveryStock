import { runBaseline, runFixedOrder, runOptimize } from "../api/client";

export default function ActionButtons({ sessionId, loading, onResult, onError, onLoadingChange }) {
  const disabled = !sessionId || loading;

  async function handle(apiFn, prefix) {
    onLoadingChange(true, prefix);
    onError(null);
    try {
      const result = await apiFn(sessionId);
      onResult(result);
    } catch (e) {
      onError(e.message);
    } finally {
      onLoadingChange(false, prefix);
    }
  }

  return (
    <div className="btn-row">
      <button
        disabled={disabled}
        onClick={() => handle(runBaseline, "baseline")}
      >
        すべて小口で配送
      </button>
      <button
        disabled={disabled}
        onClick={() => handle(runFixedOrder, "fixed_order")}
      >
        日付・商品ごとの発注数は固定で最適化
      </button>
      <button
        className="primary"
        disabled={disabled}
        onClick={() => handle(runOptimize, "optimize")}
      >
        最適化を実行
      </button>
    </div>
  );
}
