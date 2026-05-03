# Architecture

## フォルダ構成

```
src/        # アプリ本体
spec/       # 仕様書
tests/      # テストコード
data/
├── input/  # 入力データ（Excel）
└── output/ # 計算結果（Excel）
notebooks/  # 探索・試作用（本体コードではない）
```

---

## モジュール構成

| ファイル | 役割 | 仕様書 | テスト |
|---|---|---|---|
| `src/app.py` | Streamlit UI | `spec/app_spec.md` | `tests/test_app.py`（オプション） |
| `src/optimizer.py` | 最適化ロジック | `spec/optimizer_spec.md` | `tests/test_optimizer.py` |
| `src/charts.py` | グラフ描画関数 | `spec/charts_spec.md` | `tests/test_charts.py` |
| `requirements.txt` | 依存パッケージ | — | — |
| `pytest.ini` | pytest設定（`pythonpath = src`） | — | — |
| `tests/conftest.py` | テスト共通フィクスチャ | — | — |

---

## データフロー

```
Excel入力
    ↓
optimizer.py:load_excel()   # データ読み込み
    ↓
optimizer.py:optimize()     # 最適化計算（PuLP / CBC）
    ↓
charts.py:plot_*()          # グラフ描画（matplotlib）
    ↓
app.py                      # Streamlit で表示・ダウンロード
```

---

## 仕様書と要件IDの対応

| 仕様書 | 要件ID prefix | 対象 |
|---|---|---|
| `spec/optimizer_spec.md` | `O-*` | 最適化ロジック・制約条件 |
| `spec/charts_spec.md` | `C-*` | グラフ描画関数 |
| `spec/app_spec.md` | `A-*` | UI層 |

---

## UIフレームワーク

**現在**: Streamlit

**起動方法**:
```bash
python -m streamlit run src/app.py
```

ブラウザ: `http://localhost:8501`

**依存パッケージ**:
```bash
pip install -r requirements.txt
```
