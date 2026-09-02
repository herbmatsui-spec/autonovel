# 実装計画: MarketingAgent 修復 + Apache AGE GraphRAG 連携

対象: 課題 #3 (MarketingAgent 28%) + 課題 #4 (Apache AGE GraphRAG 41%)
目的: 低性能 LLM でも迷わないよう、各ステップを 1 ファイル / 1 関数 / 1 テスト単位の極小タスクに分解。
合計 36 ステップ (MarketingAgent 18 + GraphRAG 18)。

---

## 前提確認 (Phase 0)

| # | タスク | 確認コマンド / 期待結果 |
|---|---|---|
| 0.1 | `MarketingAgent` の現状読了 | `cat src/agents/marketing.py` で line 27 の `ValueError` を確認 |
| 0.2 | 既存 router 確認 | `cat src/backend/routers/marketing.py` で POST スタブ (line 35-39) を確認 |
| 0.3 | 既存テスト確認 | `ls tests/unit/ | grep marketing` → **0 件** 確認 |
| 0.4 | `AgeClient` の脆弱部分特定 | `cat src/services/age_client.py` line 38-45 の文字列マッチ確認 |
| 0.5 | `get_all_nodes` 未実装確認 | `rg get_all_nodes src/` → `graph_pipeline.py:97` のみ |
| 0.6 | 既存 docker AGE 設定確認 | `cat docker/postgres/init.sql` で既に `CREATE EXTENSION age` 済を確認 |
| 0.7 | 既存 `RetryPolicy` 確認 | `cat src/shared/retry_policy.py` で `max_attempts=3` 既定を確認 |
| 0.8 | 既存依存確認 | `requirements.txt` に `tenacity==9.1.4` 既にあるので追加不要 |

---

## Phase A: MarketingAgent 修復 (18 ステップ)

### A-1: PromptManager DI 注入修正 (router 側)

| # | タスク | 変更ファイル / 期待差分 |
|---|---|---|
| 1 | `Depends(get_prompt_manager)` のヘルパを `src/backend/auth.py` 末尾に追加 | 既存 `require_api_key` の隣に `get_prompt_manager` を定義し `prompts.manager.PromptManager` の Singleton を返す |
| 2 | `src/core/container/app.py` を編集し `pm` プロバイダを Singleton で参照可能化 | 既に line 69 で `providers.Singleton("prompts.manager.PromptManager")` 定義済 — 変更不要、存在だけ確認 |
| 3 | `src/backend/routers/marketing.py:16` の `generate_marketing` に `prompt_manager: Any = Depends(get_prompt_manager)` を追加 | 関数シグネチャに DI を 1 行追加 |
| 4 | router 内で `prompt_manager` を `execute_service_workflow` の `kwargs` に追加 | `kwargs={"book_id": ..., "latest_ep": ..., "prompt_manager": prompt_manager}` |
| 5 | `src/backend/workflows/marketing_generation_workflow.py:23` 周辺で `prompt_manager` を受け取り `self.marketing` 生成に渡す | `self.marketing` をその場で組み立て直す最小実装 (1 ブロック) |

### A-2: marketing_agent.py の DI 改善

| # | タスク | 期待差分 |
|---|---|---|
| 6 | `src/agents/marketing.py:26-27` の `raise ValueError` を `self.prompt_manager = prompt_manager or PromptManager()` に置換 | None 許容、フォールバック生成 |
| 7 | `generate_pack` の `result.get("metadata", {})` を `result.get("metadata", {}) or {}` に修正 (空 dict フォールバック) | 1 行修正 |
| 8 | `result.get("metadata", {})` 全体を `{"title": ..., "synopsis": ..., "tags": []}` のセーフデフォルトに変更 | None / キー欠落双方に安全 |
| 9 | 戻り値に `metadata` キーが無い時に LLM の生レスポンスを返す分岐を追加 | `if "metadata" not in result: return {"raw": result}` の 2 行追加 |

### A-3: POST スタブ実装

| # | タスク | 期待差分 |
|---|---|---|
| 10 | `src/backend/routers/marketing.py:35-39` のスタブを GET (line 42-50) と同じ実装に置換 | `engine = get_engine(api_key)` を使い `create_export_package` を呼ぶ |
| 11 | POST 用に `MarketingExportRequest` (api_key のみ) を `src/models/api_schemas.py` に追加 | 既存 `MarketingGenerateRequest` の隣に 5 行追加 |
| 12 | POST 側で Pydantic モデル `req: MarketingExportRequest` を受け取り `api_key` 検証 | `validate_api_key_or_raise(req.api_key)` を 1 行追加 |
| 13 | POST レスポンスを GET と同じ `Response(content=zip_data, media_type="application/zip", headers={...})` で返す | GET と同一ロジックを再利用 |

### A-4: テスト追加 (5 ケース)

| # | タスク | テストファイル / 期待結果 |
|---|---|---|
| 14 | `tests/unit/test_marketing_agent.py` 新規作成 (1 ファイル目) | import + fixture セットアップ 10 行 |
| 15 | `test_generate_pack_success` — LLM が正常 JSON を返すケース | `agent.generate_pack(...) == {"title": ..., ...}` |
| 16 | `test_generate_pack_missing_metadata_key` — LLM が metadata キー欠落 JSON を返すケース | フォールバック dict が返る |
| 17 | `test_create_export_package_zip` — repo モックで ZIP が bytes で返り `export_*.zip` 命名 | `zip_filename.startswith("export_")` |
| 18 | `test_post_export_package_endpoint` — `client.post("/api/marketing/export_package/1", json={"api_key": "..."})` で 200 + application/zip | TestClient 利用 |

---

## Phase B: Apache AGE GraphRAG 連携 (18 ステップ)

### B-1: docker-compose を apache/age-postgresql:16 ベースに移行

| # | タスク | 期待差分 |
|---|---|---|
| 19 | `docker/postgres/Dockerfile` のビルドスクリプトを削除 (pgvector + AGE のソースビルド廃止) | `FROM apache/age-postgresql:16-pgvector` の 1 行に短縮 |
| 20 | `docker-compose.yml:62` の `build: ./docker/postgres` を `image: apache/age-postgresql:16-pgvector` に置換 | build 不要、image 直接指定 |
| 21 | `docker-compose.prod.yml` があれば同じ修正 | 同上 |
| 22 | `docker/postgres/init.sql` に `CREATE EXTENSION IF NOT EXISTS vector;` を先頭に追加 (pgvector 同梱版を使うので念のため) | 既存 line 2 を `IF NOT EXISTS` に修正 |

### B-2: age_client.py の文字列マッチ脱却

| # | タスク | 期待差分 |
|---|---|---|
| 23 | `src/services/age_client.py:1` に `from sqlalchemy.exc import IntegrityError, ProgrammingError` 追加 | import 2 行 |
| 24 | `init_graph` の except 句を `except (IntegrityError, ProgrammingError)` で捕捉し `pgcode` が `"42P04"` (duplicate_graph) かチェック | "already exists" 文字列マッチを削除 |
| 25 | `init_graph` にリトライデコレータを適用 (`tenacity.retry(stop=stop_after_attempt(3), wait=wait_exponential)`) | `@retry` を関数直上に追加 |
| 26 | `upsert_node` / `upsert_edge` にも同じリトライを適用 | 各関数に `@retry` |

### B-3: graph_pipeline.py の `existing_nodes` 修正

| # | タスク | 期待差分 |
|---|---|---|
| 27 | `src/services/age_client.py` に `get_all_nodes(self, session, graph_name=None) -> list[dict]` メソッド追加 | `MATCH (n) RETURN n.name AS name, labels(n) AS labels` を cypher() で実行 |
| 28 | `src/services/graph_pipeline.py:97` の `age_client.get_all_nodes(session)` を **無条件で** 呼ぶよう変更 | `if settings.DATABASE_URL.startswith("postgresql") else []` を削除し常に呼ぶ |
| 29 | `graph_pipeline.py:97` で `AgeClient` の `get_all_nodes` が SQLite 環境では例外を返すので `try/except` で握りつぶしフォールバック | 4 行の try/except 追加 |
| 30 | ロールバック後のリトライ (`session.rollback()` 後に再度 `upsert_*`) を `update_knowledge_graph` に追加 | for ループ全体を while + attempt < 3 で囲む |

### B-4: テスト追加 (testcontainers + 既存モック強化)

| # | タスク | 期待差分 |
|---|---|---|
| 31 | `requirements.txt` に `testcontainers[postgres]==4.8.0` を追加 (1 行) | AGE テスト専用 |
| 32 | `tests/integration/test_graphrag_age.py` 新規作成 (`@pytest.mark.skipif` で testcontainers 未導入時は skip) | 先頭 5 行で skip 設定 |
| 33 | `test_age_init_graph_idempotent` — testcontainer で Postgres+AGE を起動 → `init_graph` を 2 回呼んで両方 True 確認 | `PostgresContainer("apache/age-postgresql:16-pgvector")` 利用 |
| 34 | `test_age_upsert_node_dedup` — 同じ name/label で 2 回 `upsert_node` → ノード数 1 確認 | cypher 結果カウント |
| 35 | `test_age_sqlstate_not_string_match` — monkeypatch で `pgcode=42P04` を発生させ `init_graph` が True を返す | `MagicMock(exc=IntegrityError(...))` を使用 |
| 36 | `tests/unit/test_graphrag.py` 末尾に `test_get_all_nodes_returns_empty_on_sqlite` 追加 (1 ケース) | SQLite 環境で空 dict 返却 |

---

## 検証コマンド (Phase 最後にまとめて実行)

```bash
# MarketingAgent
pytest tests/unit/test_marketing_agent.py -v

# GraphRAG (unit のみ)
pytest tests/unit/test_graphrag.py -v

# GraphRAG (integration — Docker 必須)
pytest tests/integration/test_graphrag_age.py -v -m age

# Lint
ruff check src/agents/marketing.py src/backend/routers/marketing.py src/services/age_client.py src/services/graph_pipeline.py

# 全体回帰
pytest tests/ -q
```

---

## ロールバック戦略

| 変更 | リスク | ロールバック |
|---|---|---|
| `docker/postgres/Dockerfile` 削除 | ローカル Docker ビルド不可 | `git revert` で Dockerfile 復活 |
| `age_client.init_graph` の SQLSTATE 化 | 既存テスト (`test_age_client_methods`) が「bool」だけ検証しているので影響なし | 不要 |
| `get_all_nodes` 新メソッド | 既存呼び出しなし (`grep` 確認済) | メソッド削除で戻る |

---

## 工数見積

| Phase | 内容 | 想定工数 |
|---|---|---|
| Phase 0 | 現状確認 | 0.5日 |
| Phase A-1 (1-5) | PromptManager DI 修正 | 1日 |
| Phase A-2 (6-9) | marketing_agent 修正 | 0.5日 |
| Phase A-3 (10-13) | POST スタブ実装 | 0.5日 |
| Phase A-4 (14-18) | テスト 5ケース | 1日 |
| Phase B-1 (19-22) | docker-compose 移行 | 0.5日 |
| Phase B-2 (23-26) | age_client リファクタ | 1日 |
| Phase B-3 (27-30) | graph_pipeline 修正 | 1日 |
| Phase B-4 (31-36) | テスト追加 | 1.5日 |
| 検証 | 全体回帰 + lint | 0.5日 |
| **合計** | | **8日 (= 1.6週)** |

元見積 (MarketingAgent 1週 + GraphRAG 2週 = 3週) より 1.4週短縮可能。
