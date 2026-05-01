import { downloadExcel } from "../../utils/base64";

export default function ExcelDownload({ base64, filename }) {
  return (
    <button className="primary" onClick={() => downloadExcel(base64, filename)}>
      結果を Excel でダウンロード
    </button>
  );
}
