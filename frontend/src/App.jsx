import { useState } from "react";
import FileUpload from "./components/FileUpload";
import ActionButtons from "./components/ActionButtons";
import LoadingSpinner from "./components/LoadingSpinner";
import ResultsPanel from "./components/results/ResultsPanel";

export default function App() {
  const [sessionId, setSessionId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [filePrefix, setFilePrefix] = useState("result");

  function handleUploaded(sid) {
    setSessionId(sid);
    setResult(null);
    setError(null);
  }

  function handleReset() {
    setSessionId(null);
    setResult(null);
  }

  function handleResult(data) {
    setResult(data);
    setError(null);
  }

  return (
    <>
      <h1>入荷最適化</h1>

      <FileUpload onUploaded={handleUploaded} onReset={handleReset} />

      <ActionButtons
        sessionId={sessionId}
        loading={loading}
        onResult={handleResult}
        onError={setError}
        onLoadingChange={(v) => {
          setLoading(v);
          if (v) {
            setResult(null);
            setError(null);
          }
        }}
      />

      {loading && <LoadingSpinner />}

      {error && !loading && (
        <div className="error-box">{error}</div>
      )}

      {result && !loading && (
        <ResultsPanel result={result} filePrefix={filePrefix} />
      )}
    </>
  );
}
