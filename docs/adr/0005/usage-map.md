# DI Container Usage Map

Generated: 2026-07-17

## Container: `config.container.Container` (旧)

| ファイル | 行 | 使用プロバイダ | 用途 |
|---|---|---|---|
| `src/backend/server.py` | 26 | Container() | FastAPI 起動 |
| `src/backend/sse.py` | 25,85 | Container() | SSE進捗配信 |
| `src/backend/tasks.py` | 116,137,234 | Container() | タスクワーカー |
| `src/backend/task_helpers.py` | 5 | Container() | ヘルパー |
| `src/backend/engine_helpers.py` | 5 | Container.db() | DB注入 |
| `src/backend/routers/health.py` | 4 | Container | ヘルスチェック |
| `src/backend/routers/books.py` | 4 | Container | ルーター |
| `src/backend/routers/episodes.py` | 2 | Container | ルーター |
| `src/backend/routers/plots.py` | 2 | Container | ルーター |
| `src/backend/routers/patches.py` | 6 | Container | ルーター |
| `src/backend/routers/issues.py` | 6 | Container | ルーター |
| `src/backend/routers/tasks.py` | 7 | Container | ルーター |
| `src/backend/routers/prompt_versions.py` | 4 | Container | ルーター |
| `src/backend/routers/metrics.py` | 3 | AppContainer as Container | ルーター |
| `src/backend/routers/misc.py` | 4 | AppContainer as Container | ルーター |
| `src/services/prompt_version_service.py` | 20-21 | Provide["config.container.AppContainer.uow"] | サービス |
| `tests/test_uow.py` | 11 | Container | テスト |
| `tests/test_vector_store_lifecycle.py` | 4 | Container | テスト |
| `tests/test_outbox_worker.py` | 12 | Container | テスト |
| `tests/test_prompt_version_manager.py` | 11 | Container | テスト |
| `tests/test_background_worker.py` | 15 | Container | テスト |
| `test_db.py` | 6 | Container | テスト |
| `archive/legacy_scripts/modify_tasks.py` | 39 | Container | アーカイブ |

## Container: `src.core.container.AppContainer`

| ファイル | 行 | 使用プロバイダ | 用途 |
|---|---|---|---|
| `src/backend/engine_helpers.py` | 14-20 | AppContainer | エンジン生成 |
| `src/backend/tasks.py` | 138-148 | AppContainer | バックグラウンド |
| `src/backend/routers/metrics.py` | 3 | AppContainer as Container | ルーター |
| `src/backend/routers/misc.py` | 4 | AppContainer as Container | ルーター |
| `streamlit_app/proxy.py` | 4 | AppContainer | Streamlit |
| `tests/test_zamaa_generation.py` | 6 | AppContainer as Container | テスト |
| `tests/unit/test_container.py` | 1 | AppContainer | テスト |
| `tests/unit/test_llm_service_di.py` | 6 | LLMGenerateResultProxy | テスト |
| `tests/unit/test_container.py` | 1 | AppContainer | テスト |
| `tests/perf_container_test.py` | 3 | AppContainer | テスト |
| `tests/test_backend/test_engine.py` | 4 | AppContainer | テスト |
| `tests/integration/test_workflow.py` | 145-408 | AppContainer | テスト |
