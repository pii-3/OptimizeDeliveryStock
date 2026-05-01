import { downloadPNG } from "../../utils/base64";
import DataTable from "./DataTable";

export default function ChartSection({ title, base64, downloadFilename, tableData }) {
  return (
    <div>
      <h3>{title}</h3>
      <img
        className="chart-img"
        src={`data:image/png;base64,${base64}`}
        alt={title}
      />
      <button onClick={() => downloadPNG(base64, downloadFilename)}>
        PNG ダウンロード
      </button>
      {tableData && (
        <div style={{ marginTop: 12 }}>
          <DataTable data={tableData} />
        </div>
      )}
    </div>
  );
}
