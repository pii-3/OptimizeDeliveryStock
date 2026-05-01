import { useRef, useState } from "react";
import { uploadFile } from "../api/client";

export default function FileUpload({ onUploaded, onReset }) {
  const inputRef = useRef(null);
  const [filename, setFilename] = useState(null);
  const [error, setError] = useState(null);
  const [uploading, setUploading] = useState(false);

  async function handleFile(file) {
    if (!file) return;
    setError(null);
    setUploading(true);
    try {
      const { session_id } = await uploadFile(file);
      setFilename(file.name);
      onUploaded(session_id);
    } catch (e) {
      setError(e.message);
      onReset();
    } finally {
      setUploading(false);
    }
  }

  function handleChange(e) {
    handleFile(e.target.files[0]);
  }

  function handleDrop(e) {
    e.preventDefault();
    handleFile(e.dataTransfer.files[0]);
  }

  return (
    <div>
      <div
        className="upload-area"
        onClick={() => inputRef.current.click()}
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
      >
        <input ref={inputRef} type="file" accept=".xlsx" onChange={handleChange} />
        {uploading ? (
          <span>アップロード中...</span>
        ) : (
          <>
            <span>Excel ファイル (.xlsx) をドラッグ＆ドロップ、またはクリックして選択</span>
            {filename && <div className="filename">✓ {filename}</div>}
          </>
        )}
      </div>
      {error && <div className="error-box">{error}</div>}
    </div>
  );
}
