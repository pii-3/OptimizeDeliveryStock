# Architecture

## フォルダ構成

```
backend/          # FastAPI バックエンド
├── main.py       # アプリエントリーポイント・CORS設定
├── routers/
│   └── optimize.py   # API エンドポイント 4本
├── services/
│   └── session_store.py  # インメモリセッション管理
├── models/
│   └── schemas.py    # Pydantic リクエスト/レスポンスモデル
└── requirements.txt  # バックエンド依存パッケージ

frontend/         # React フロントエンド (Vite + JavaScript)
├── index.html
├── vite.config.js    # dev proxy 設定
├── package.json
└── src/
    ├── main.jsx
    ├── App.jsx           # state管理 (sessionId / loading / result / error)
    ├── index.css
    ├── api/
    │   └── client.js     # fetch 関数 4本
    ├── components/
    │   ├── FileUpload.jsx
    │   ├── ActionButtons.jsx
    │   ├── LoadingSpinner.jsx
    │   └── results/
    │       ├── ResultsPanel.jsx
    │       ├── CostMetrics.jsx
    │       ├── SummaryMetrics.jsx
    │       ├── DataTable.jsx
    │       ├── ChartSection.jsx
    │       └── ExcelDownload.jsx
    └── utils/
        └── base64.js     # PNG / Excel ダウンロードヘルパー

src/              # 最適化ロジック（変更しない）
├── optimizer.py  # load_excel / optimize / optimize_fixed_order / calculate_baseline
└── charts.py     # plot_order_and_inventory_all / plot_order_and_inventory_by_product

spec/             # 仕様書
tests/            # テストコード（src/ を対象、backend/ とは独立）
data/
├── input/        # 入力データ（Excel）
└── output/       # 計算結果（Excel）
notebooks/        # 探索・試作用（本体コードではない）
```

---

## モジュール構成

| ファイル | 役割 | 仕様書 | テスト |
|---|---|---|---|
| `backend/routers/optimize.py` | FastAPI エンドポイント・KPI計算・直列化 | `spec/app_spec.md` | — |
| `backend/services/session_store.py` | インメモリセッション管理 | — | — |
| `backend/models/schemas.py` | API スキーマ定義 | — | — |
| `src/optimizer.py` | 最適化ロジック | `spec/optimizer_spec.md` | `tests/test_optimizer.py` |
| `src/charts.py` | グラフ描画関数（matplotlib） | `spec/charts_spec.md` | `tests/test_charts.py` |
| `frontend/src/App.jsx` | React UI・状態管理 | `spec/app_spec.md` | — |
| `requirements.txt` | テスト用依存パッケージ（pytest等） | — | — |
| `backend/requirements.txt` | バックエンド依存パッケージ | — | — |
| `pytest.ini` | pytest設定（`pythonpath = src`） | — | — |
| `tests/conftest.py` | テスト共通フィクスチャ | — | — |

---

## データフロー

```
ブラウザ (React / http://localhost:5173)
    ↓  POST /upload  (Excel ファイル)
backend/routers/optimize.py
    ↓  load_excel()
src/optimizer.py               # データ読み込み・パース
    ↓  DataFrames をセッションに保存
    ↓
    ↓  POST /baseline | /fixed_order | /optimize
backend/routers/optimize.py
    ↓  calculate_baseline() | optimize_fixed_order() | optimize()
src/optimizer.py               # 最適化計算（PuLP / CBC）
    ↓  plot_*()
src/charts.py                  # グラフ描画（matplotlib → base64 PNG）
    ↓  JSON レスポンス（結果 + base64チャート + base64 Excel）
ブラウザ (React)               # 表示・ダウンロード
```

---

## API エンドポイント

| メソッド | パス | 説明 |
|---|---|---|
| `POST` | `/upload` | Excel アップロード → `{ session_id }` |
| `POST` | `/baseline` | 全小口ベースライン計算 |
| `POST` | `/fixed_order` | 発注数固定で最適化 |
| `POST` | `/optimize` | 完全最適化 |

リクエスト・レスポンスの詳細は `backend/models/schemas.py` を参照。
Swagger UI: `http://localhost:8000/docs`

---

## 仕様書と要件IDの対応

| 仕様書 | 要件ID prefix | 対象 |
|---|---|---|
| `spec/optimizer_spec.md` | `O-*` | 最適化ロジック・制約条件 |
| `spec/charts_spec.md` | `C-*` | グラフ描画関数 |
| `spec/app_spec.md` | `A-*` | UI層 |

---

## 起動方法

### バックエンド

```bash
cd backend
pip install -r requirements.txt   # 初回のみ
uvicorn main:app --reload --port 8000
```

### フロントエンド

```bash
cd frontend
npm install   # 初回のみ
npm run dev
# → http://localhost:5173
```

### テスト（src/ のロジックのみ対象）

```bash
pytest        # リポジトリルートで実行
```

---

## 設計上の注意点

### `matplotlib.use("Agg")` の順序
`src/charts.py` がモジュール先頭で `import matplotlib.pyplot as plt` を行うため、
`backend/main.py` の**ローカルモジュール import より前**に `matplotlib.use("Agg")` を配置している。
順序を変えるとサーバー起動時にクラッシュする。

### `sys.path` による `src/` の参照
`backend/main.py` が `sys.path.insert(0, .../src)` でパスを通しているため、
`optimizer.py` / `charts.py` はパッケージ化せずそのまま使用できる。

### 日付の JSON 直列化
pandas の `Timestamp` 型は JSON 非対応のため、`optimizer.py` から受け取った DataFrame の
日付列は `dt.strftime("%Y-%m-%d")` で文字列変換してからレスポンスに含める。

### セッション管理
アップロードのたびに `clear_all()` で旧セッションを全削除し、新しい `session_id` を発行する。
単一ユーザーのローカルアプリを前提とした設計。
