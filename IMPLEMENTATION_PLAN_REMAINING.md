# 残りタスク実装計画書: テスト失敗修正

## 概要

前回の実装で発見された 3 つのテスト失敗を修正する。

---

## Issue 1: `test_migration_ordering` 失敗

### 原因
`ScriptDirectory.walk_revisions("base", "head")` は **head から base へ向かって降順** でリビジョンを返す（`0013, 0012, 0011, 0004, 0003, 0002, 0001, 0000`）。テストは昇順（base → head）を期待しているため失敗する。

### 修正方針
テストを修正して、降順で返ってくることを正しく検証するか、または `walk_revisions("head", "base")` を使って昇順で取得する。

推奨: `walk_revisions("head", "base")` を使用し、昇順で取得してから検証。

### 変更ファイル
- `tests/test_migrations.py`: `test_migration_ordering` 関数修正

---

## Issue 2: `test_streaming_generator_with_optin_config` 失敗

### 原因
`_stream_generator(input_data: EasyModeInput, request: Request)` は第2引数 `Request` オブジェクトを必須としているが、テストでは `inp` しか渡していない。

### 修正方針
テスト内でモック `Request` オブジェクトを作成して渡す。`starlette.testclient.TestClient` や `fastapi.Request` のモックを使用。

### 変更ファイル
- `tests/unit/test_easy_mode_optin.py`: `test_streaming_generator_with_optin_config` 関数修正

---

## Issue 3: `test_execute_generation` 失敗

### 原因
`src/backend/routers/easy_mode.py:46` で `rag_service.build_rag_context(...)` を `await` なしで呼び出している。この関数は `async def` で定義されているため、コルーチンオブジェクトが返され、アンパック時に `TypeError: cannot unpack non-iterable coroutine object` が発生する。

### 修正方針
`await rag_service.build_rag_context(...)` に修正。

### 変更ファイル
- `src/backend/routers/easy_mode.py`: `execute_generation` 関数内の呼び出し修正

---

## 統合スケジュール

| 順序 | タスク | 所要時間 |
|------|--------|----------|
| 1 | `test_migration_ordering` 修正 | 5分 |
| 2 | `test_easy_mode_optin` streaming テスト修正 | 10分 |
| 3 | `execute_generation` の `await` 追加 | 5分 |
| 4 | 全テスト実行・確認 | 10分 |

**総工数目安: 30分**

---

## チェックリスト

### Issue 1 完了確認
- [ ] `test_migration_ordering` がパスする
- [ ] マイグレーション順序検証が正しく動作する

### Issue 2 完了確認
- [ ] `test_streaming_generator_with_optin_config` がパスする
- [ ] モック Request オブジェクトで切断判定もテスト可能

### Issue 3 完了確認
- [ ] `test_execute_generation` がパスする
- [ ] `execute_generation` 内で `await` が正しく使われている
- [ ] 他の非同期呼び出しでも同様の問題がないか確認

---

## リスクと対策

| リスク | 影響度 | 対策 |
|--------|--------|------|
| `execute_generation` 修正で他の呼び出し箇所に影響 | 中 | 同ファイル内の他の `build_rag_context` 呼び出しも確認 |
| モック Request の実装不備で別エラー | 低 | `is_disconnected` をモックする最小実装で十分 |

---

## 今後の予防策

- 非同期関数呼び出し時は必ず `await` を付けるようコードレビューで確認
- alembic の `walk_revisions` の挙動をドキュメント化
- ストリーミングテスト用の共通モックヘルパーを `conftest.py` に追加検討