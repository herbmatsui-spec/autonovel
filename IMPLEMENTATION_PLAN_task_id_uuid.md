# task_id 衝突防止 — UUID 導入実装計画書

## 概要

秒単位ID（`f"{prefix}_{int(time.time())}"`）をUUID（`uuid.uuid4().hex[:12]`）に置換し、並列リクエスト時のtask_id衝突を防止する。

## 対象ファイル

- `src/backend/server.py`

## 対象箇所（11箇所）

| # | 行 | 旧形式 | 新形式 |
|---|-----|--------|--------|
| 1 | 151 | `refine_erotic_{int(time.time())}` | `refine_erotic_{uuid.uuid4().hex[:12]}` |
| 2 | 172 | `easy_{int(time.time())}` | `easy_{uuid.uuid4().hex[:12]}` |
| 3 | 197 | `plan_gen_{int(time.time())}` | `plan_gen_{uuid.uuid4().hex[:12]}` |
| 4 | 211 | `retry_failed_{int(time.time())}` | `retry_failed_{uuid.uuid4().hex[:12]}` |
| 5 | 229 | `write_{int(time.time())}` | `write_{uuid.uuid4().hex[:12]}` |
| 6 | 254 | `write_candidates_{int(time.time())}` | `write_candidates_{uuid.uuid4().hex[:12]}` |
| 7 | 279 | `plot_expand_{int(time.time())}` | `plot_expand_{uuid.uuid4().hex[:12]}` |
| 8 | 299 | `plot_candidates_{int(time.time())}` | `plot_candidates_{uuid.uuid4().hex[:12]}` |
| 9 | 319 | `plot_rebuild_{int(time.time())}` | `plot_rebuild_{uuid.uuid4().hex[:12]}` |
| 10 | 356 | `critique_{int(time.time())}` | `critique_{uuid.uuid4().hex[:12]}` |
| 11 | 396 | `import_{int(time.time())}` | `import_{uuid.uuid4().hex[:12]}` |

## 事前確認事項

- `uuid` は既に line 68 で import 済み
- `time` は line 5 で import 済み
- 置換による副作用なし（task_id は文字列としてのみ使用

---

## 72ステップ実装計画

### フェーズ1: 準備・分析（ステップ1-10）

| ステップ | アクション | 詳細 |
|---------|-----------|------|
| 1 | ファイルバックアップ取得 | `cp src/backend/server.py src/backend/server.py.bak` |
| 2 | 現import文確認 | line 5 の `import time` を確認 |
| 3 | uuid import確認 | line 68 の `import uuid` を確認 |
| 4 | 置換対象数確認 | 11箇所をリスト化済み（上表参照） |
| 5 | task_id使用箇所調査 | 各行のtask_idがRedis/SQLiteでどう使用されるか確認 |
| 6 | `_create_task`関数確認 | task_idの引数渡し先を調査 |
| 7 | `execute_service_workflow`確認 | task_idの受取先进行调查 |
| 8 | 旧形式 `f"xxx_{int(time.time())}"` パターンをgrep | 正確な行番号・文脈を確定 |
| 9 | 新形式 `uuid.uuid4().hex[:12]` の文字数確認 | 12文字のhex = 衝突確率ほぼゼロ |
| 10 | テスト方針立案 | 11endpointすべての置換後テスト項目一覧作成 |

---

### フェーズ2: ヘルパー関数作成（ステップ11-15）

| ステップ | アクション | 詳細 |
|---------|-----------|------|
| 11 | 新関数 `generate_task_id(prefix: str) -> str` の設計 | 引数: prefix文字列、戻り値: `f"{prefix}_{uuid.uuid4().hex[:12]}"` |
| 12 | 関数配置的場所的决定 | server.pyのimport群直後（line 68付近） |
| 13 | 関数コード記述 | ```python\ndef generate_task_id(prefix: str) -> str:\n    return f"{prefix}_{uuid.uuid4().hex[:12]}"\n``` |
| 14 | 関数定義をserver.pyに挿入 | line 68 (`import uuid`) の直後に挿入 |
| 15 | 関数定義の文法チェック | `python -m py_compile src/backend/server.py` |

---

### フェーズ3: 各endpoint置換（ステップ16-60）

#### refine_erotic（ステップ16-20）

| ステップ | アクション | 詳細 |
|---------|-----------|------|
| 16 | line 151 置換前確認 | `task_id = f"refine_erotic_{int(time.time())}"` |
| 17 | 旧文を新文に置換 | `task_id = generate_task_id("refine_erotic")` |
| 18 | 置換後確認 | `print(task_id)` で形式確認可能（ログ追加） |
| 19 | 関連line確認 | line 152, 155, 167 のtask_id使用箇所チェック |
| 20 | 静的構文チェック | `python -m py_compile` |

#### easy_mode/generate（ステップ21-25）

| ステップ | アクション | 詳細 |
|---------|-----------|------|
| 21 | line 172 置換前確認 | `task_id = f"easy_{int(time.time())}"` |
| 22 | 旧文を新文に置換 | `task_id = generate_task_id("easy")` |
| 23 | 置換後確認 | await _create_task(task_id, ...) の引数確認 |
| 24 | 関連line確認 | line 173, 176, 193 のtask_id使用箇所チェック |
| 25 | 静的構文チェック | `python -m py_compile` |

#### plan_generation（ステップ26-30）

| ステップ | アクション | 詳細 |
|---------|-----------|------|
| 26 | line 197 置換前確認 | `task_id = f"plan_gen_{int(time.time())}"` |
| 27 | 旧文を新文に置換 | `task_id = generate_task_id("plan_gen")` |
| 28 | 置換後確認 | await _create_task(task_id, ...) の引数確認 |
| 29 | 関連line確認 | line 198, 199, 207 のtask_id使用箇所チェック |
| 30 | 静的構文チェック | `python -m py_compile` |

#### retry_failed（ステップ31-35）

| ステップ | アクション | 詳細 |
|---------|-----------|------|
| 31 | line 211 置換前確認 | `task_id = f"retry_failed_{int(time.time())}"` |
| 32 | 旧文を新文に置換 | `task_id = generate_task_id("retry_failed")` |
| 33 | 置換後確認 | await _create_task(task_id, ...) の引数確認 |
| 34 | 関連line確認 | line 212, 213, 225 のtask_id使用箇所チェック |
| 35 | 静的構文チェック | `python -m py_compile` |

#### episodes/generate（ステップ36-40）

| ステップ | アクション | 詳細 |
|---------|-----------|------|
| 36 | line 229 置換前確認 | `task_id = f"write_{int(time.time())}"` |
| 37 | 旧文を新文に置換 | `task_id = generate_task_id("write")` |
| 38 | 置換後確認 | await _create_task(task_id, ...) の引数確認 |
| 39 | 関連line確認 | line 230, 232, 250 のtask_id使用箇所チェック |
| 40 | 静的構文チェック | `python -m py_compile` |

#### episodes/generate_candidates（ステップ41-45）

| ステップ | アクション | 詳細 |
|---------|-----------|------|
| 41 | line 254 置換前確認 | `task_id = f"write_candidates_{int(time.time())}"` |
| 42 | 旧文を新文に置換 | `task_id = generate_task_id("write_candidates")` |
| 43 | 置換後確認 | await _create_task(task_id, ...) の引数確認 |
| 44 | 関連line確認 | line 255, 257, 275 のtask_id使用箇所チェック |
| 45 | 静的構文チェック | `python -m py_compile` |

#### plots/expand（ステップ46-50）

| ステップ | アクション | 詳細 |
|---------|-----------|------|
| 46 | line 279 置換前確認 | `task_id = f"plot_expand_{int(time.time())}"` |
| 47 | 旧文を新文に置換 | `task_id = generate_task_id("plot_expand")` |
| 48 | 置換後確認 | await _create_task(task_id, ...) の引数確認 |
| 49 | 関連line確認 | line 280, 282, 295 のtask_id使用箇所チェック |
| 50 | 静的構文チェック | `python -m py_compile` |

#### plots/expand_candidates（ステップ51-55）

| ステップ | アクション | 詳細 |
|---------|-----------|------|
| 51 | line 299 置換前確認 | `task_id = f"plot_candidates_{int(time.time())}"` |
| 52 | 旧文を新文に置換 | `task_id = generate_task_id("plot_candidates")` |
| 53 | 置換後確認 | await _create_task(task_id, ...) の引数確認 |
| 54 | 関連line確認 | line 300, 302, 315 のtask_id使用箇所チェック |
| 55 | 静的構文チェック | `python -m py_compile` |

#### plots/rebuild（ステップ56-60）

| ステップ | アクション | 詳細 |
|---------|-----------|------|
| 56 | line 319 置換前確認 | `task_id = f"plot_rebuild_{int(time.time())}"` |
| 57 | 旧文を新文に置換 | `task_id = generate_task_id("plot_rebuild")` |
| 58 | 置換後確認 | db.save_internal_state(task_id, ...) の引数確認 |
| 59 | 関連line確認 | line 320, 336-340, 342, 352 のtask_id使用箇所チェック |
| 60 | 静的構文チェック | `python -m py_compile` |

#### critique/optimize（ステップ61-65）

| ステップ | アクション | 詳細 |
|---------|-----------|------|
| 61 | line 356 置換前確認 | `task_id = f"critique_{int(time.time())}"` |
| 62 | 旧文を新文に置換 | `task_id = generate_task_id("critique")` |
| 63 | 置換後確認 | await _create_task(task_id, ...) の引数確認 |
| 64 | 関連line確認 | line 357, 358, 369, 370 のtask_id使用箇所チェック |
| 65 | 静的構文チェック | `python -m py_compile` |

#### chapters/import（ステップ66-70）

| ステップ | アクション | 詳細 |
|---------|-----------|------|
| 66 | line 396 置換前確認 | `task_id = f"import_{int(time.time())}"` |
| 67 | 旧文を新文に置換 | `task_id = generate_task_id("import")` |
| 68 | 置換後確認 | await _create_task(task_id, ...) の引数確認 |
| 69 | 関連line確認 | line 397, 399, 412 のtask_id使用箇所チェック |
| 70 | 静的構文チェック | `python -m py_compile` |

---

### フェーズ4: 最終検証（ステップ71-72）

| ステップ | アクション | 詳細 |
|---------|-----------|------|
| 71 | 全置換完了確認 | grepで `{int(time.time())}` の残存を最終確認 |
| 72 | 全文法チェック | `python -m py_compile src/backend/server.py` + 必要なら `ruff check` |

---

## 置換前後のtask_id形式比較

```
【旧形式】plan_gen_1752225321        ← 同秒内で衝突発生
【新形式】plan_gen_a1b2c3d4e5f6      ← 衝突確率ほぼゼロ
```

## リスク評価

| 項目 | 評価 |
|------|------|
| 技術リスク | 極小（uuidは標準ライブラリ、破壊的変更なし） |
| 影響範囲 | task_id生成のみ（論理構造変更なし） |
| ロールバック | 备份ファイルから即座に復元可能 |

## 工数実績

| フェーズ | ステップ数 | 想定時間 |
|---------|-----------|----------|
| 準備・分析 | 10 | 0.1h |
| ヘルパー関数作成 | 5 | 0.1h |
| 各endpoint置換 | 55 | 0.2h |
| 最終検証 | 2 | 0.1h |
| **合計** | **72** | **0.5h** |