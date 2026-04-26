# 協働ガイドライン

## 概要
このファイルはClaudeとの効率的な協働方法を記録しています。

---

## ファイル構成

```
spec/               # 仕様書
├── optimizer_spec.md
├── app_spec.md
└── charts_spec.md

tests/              # テストコード
├── conftest.py
├── test_optimizer.py
└── test_charts.py

data/
├── input/          # 入力データ（Excel）
└── output/         # 計算結果（Excel）

notebooks/
├── 入荷の最適化.ipynb       # 原版ノートブック（参考）
└── visualization.ipynb    # グラフ試作用（使い捨て）

app.py              # Streamlit UI（本体）
optimizer.py        # 最適化ロジック（本体）
charts.py           # グラフ関数（予定）

MODEL.md            # 数学的仕様書
requirements.txt    # 依存パッケージ
```

---

## 開発フロー

### 仕様駆動開発（推奨）

1. **spec/ に仕様を記述** — 要件を言語化（要件ID: C-1, O-1 など）
2. **tests/ にテストコードを追加**（赤：テスト失敗）
3. **実装コード（charts.py など）を追加**（緑：テスト合格）
4. **リファクタリング・ドキュメント化**（黄：コード改善）
5. **git commit で仕様番号を参照**
   ```bash
   git commit -m "feat: implement C-1 (spec/charts_spec.md)"
   ```

### モデル変更時

1. **MODEL.md を更新** — 新しい式・制約を記述
2. **optimizer.py を更新** — コードに実装、`[MODEL.md:セクション名]` コメント付け
3. **git commit** — MODEL.md と optimizer.py を一緒にコミット

例:
```bash
git commit -m "feat: add XXX constraint (MODEL.md + optimizer.py)"
```

### グラフ・可視化追加時

1. **spec/charts_spec.md に要件を記述** — UI、グラフ形式など
2. **tests/test_charts.py にテストを追加**（赤）
3. **notebooks/visualization.ipynb で試作** — `from charts import ...` でインポート
4. **charts.py に関数化** — 良い形が決まったら切り出す（緑）
5. **app.py に統合** — Streamlit で表示
6. **git commit で仕様番号を参照**

### Streamlit アプリ修正時

1. **app.py を直接編集**
2. **ローカルで動作確認** — `streamlit run app.py`
3. **git commit**

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

- **notebooks/**: 探索・試作用のみ。本体コードではない
- 試作完了後は削除するか、参考資料として放置
- 削除しても `.gitignore` で git に追跡されない

---

## 依存パッケージ

**requirements.txt** から自動インストール:
```bash
pip install -r requirements.txt
```

パッケージ追加時は requirements.txt を更新し、Claudeに報告。

---

## 起動方法

```bash
python -m streamlit run app.py
```

ブラウザ: `http://localhost:8501`

---

## トラブルシューティング

### 最適解が見つからない場合
- MODEL.md の制約を確認
- `optimizer.py` の制約ロジックを検証
- ソルバーログ確認: `model.solve()` の `msg=1` に変更

### グラフがおかしい
- `notebooks/visualization.ipynb` で再検証
- `charts.py` の関数を修正
- `app.py` で正しく呼び出されているか確認
