# 協働ガイドライン

## 概要
このファイルはClaudeとの効率的な協働方法を記録しています。

---

## フォルダ構成

```
backend/    # FastAPI バックエンド
frontend/   # React フロントエンド（Vite + JavaScript）
src/        # 最適化ロジック（optimizer.py, charts.py）
spec/       # 仕様書（モジュール構成・要件はここに記載）
tests/      # テストコード（src/ のロジックが対象）
data/
├── input/  # 入力データ（Excel）
└── output/ # 計算結果（Excel）
notebooks/  # 探索・試作用（本体コードではない）
```

詳細は `spec/architecture.md` を参照。

---

## 開発フロー

### 仕様駆動開発（推奨）

**基本原則**: 仕様 → テスト → 実装の順を守る。実装より先にテストを書くことで、仕様の曖昧さを早期に発見できる。

---

#### ステップ 1: 仕様を記述する

**自分でやること**: 要件の目的・入出力・表示内容を言語化し、要件IDを付与する。

**Claudeへの指示例**:
```
spec/charts_spec.md に C-4 の要件を追加して。
目的: ○○を可視化したい。
入力: decision_variables DataFrame
出力: matplotlib Figure
表示内容: X軸は日付、Y軸は○○、折れ線グラフ
```

**確認**: 「これはテストできるか？」と自問する。曖昧な表現（"良い感じに"など）は修正する。

---

#### ステップ 2: テストを追加する（赤）

**Claudeへの指示例**:
```
spec/charts_spec.md の C-4 に基づいて tests/test_charts.py にテストを追加して。
実装はまだしないで。
```

**確認**:
```bash
pytest tests/test_charts.py::test_C4_xxx -v
# → FAILED になること（赤）
```

---

#### ステップ 3: 実装する（緑）

**Claudeへの指示例**:
```
spec/charts_spec.md の C-4 と tests/test_charts.py のテストを参照して、
charts.py に plot_xxx() を実装して。
```

**確認**:
```bash
pytest tests/test_charts.py::test_C4_xxx -v
# → PASSED になること（緑）
```

---

#### ステップ 4: リファクタリング（黄）

**Claudeへの指示例**:
```
charts.py の plot_xxx() をリファクタリングして。テストは変えないで。
```
または `/simplify` スラッシュコマンドを使う。

**確認**:
```bash
pytest -v
# → 全テストが引き続き PASSED
```

---

#### ステップ 5: コミット

**Claudeへの指示例**:
```
C-4 の実装が完了したのでコミットして。
```

**コミットメッセージの形式**:
```bash
git commit -m "feat: implement C-4 (spec/charts_spec.md)"
```

### グラフ・可視化追加時

1. **spec/charts_spec.md に要件を記述** — UI、グラフ形式など
2. **tests/test_charts.py にテストを追加**（赤）
3. **charts.py に実装**（緑）
4. **backend/routers/optimize.py で `_build_response()` に統合**
5. **frontend の ResultsPanel.jsx に表示を追加**
6. **git commit で仕様番号を参照**

### UI層の修正時

1. **spec/app_spec.md に要件を記述**（新規 or 既存要件の更新）
2. **バックエンド変更が必要なら `backend/routers/optimize.py` を修正**
3. **フロントエンドのコンポーネントを修正**（`frontend/src/components/` 以下）
4. **ローカルで動作確認** — 起動方法は `spec/architecture.md` を参照
5. **git commit で仕様番号を参照**

### テスト実行

```bash
# 全テスト実行
pytest

# 特定の要件テスト
pytest tests/test_charts.py::TestC1_InventoryAllChart

# 詳細表示
pytest -v
```

---

## ノートブックの役割

通常の開発フローには含まない。動作を手元で試したい時だけ使う。

**Claudeへの指示例**:
```
○○を確認するためのノートブックを notebooks/ に作って。
```

作成後は自分で自由に編集・実行する。使い終わったら削除してよい（`.gitignore` で追跡されない）。

---

## 依存パッケージ

| 対象 | ファイル | 用途 |
|---|---|---|
| バックエンド | `backend/requirements.txt` | FastAPI, uvicorn, optimizer 依存 |
| テスト | `requirements.txt`（ルート） | pytest, optimizer 依存 |
| フロントエンド | `frontend/package.json` | React, Vite |

パッケージ追加時は対応する requirements ファイルを更新し、Claude に報告。

起動方法・インストール手順は `spec/architecture.md` を参照。

---

## トラブルシューティング

### 最適解が見つからない場合
- `spec/optimizer_spec.md` の数学モデル・制約条件を確認
- `optimizer.py` の制約ロジックを検証
- ソルバーログ確認: `model.solve()` の `msg=1` に変更

### グラフがおかしい
- `src/charts.py` の関数を確認・修正
- `backend/routers/optimize.py` の `_build_response()` で正しく呼び出されているか確認
- `http://localhost:8000/docs` の Swagger UI で API レスポンスの `chart_c1_base64` を直接確認
- 手元で試したい場合はノートブックを作成して検証

### フロントエンドが API に繋がらない
- バックエンドが `http://localhost:8000` で起動しているか確認
- `frontend/vite.config.js` の proxy 設定（`/api` → `localhost:8000`）を確認
- ブラウザの開発者ツールでネットワークエラーを確認
