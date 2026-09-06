# テストカバレッジ率向上 実装計画書

## 現状分析サマリー

| 指標 | 現在値 | 目標値 | ギャップ |
|------|--------|--------|---------|
| 行カバレッジ | 25.83% | 80% | +54.17% |
| ステートメントカバレッジ | 30.79% | 80% | +49.21% |
| ブランチカバレッジ | 6.09% | 80% | +73.91% |
| 総ステートメント数 | 22,612 | - | - |
| カバー済み行 | 6,963 | 18,090 | +11,127 |

### 0%カバレッジのファイル（主要50ファイル）
- **src/agents/writing/_writing.py** (226 statements)
- **src/agents/writing_scheduler.py** (191 statements)
- **src/backend/background.py** (177 statements)
- **src/backend/workflows/writing_langgraph.py** (343 statements)
- **src/backend/workflows/plot_langgraph.py** (88 statements)
- **src/backend/sanitizer.py** (490 statements)
- **src/backend/database/core.py** (245 statements)
- **src/backend/database/uow.py** (153 statements)
- **src/infrastructure/api/api_client.py** (216 statements)
- **src/services/auto_workflow_pipeline.py** (119 statements)
- **src/core/async_executor.py** (125 statements)
- **src/core/otel_setup.py** (107 statements)
- **src/backend/engine_context.py** (173 statements)
- **src/backend/engine_critique.py** (119 statements)
- **src/backend/engine_narrative.py** (143 statements)
- **src/backend/engine_utils.py** (148 statements)
- **src/services/redis_cache.py** (357 statements)
- **src/services/vector_store.py** (271 statements)
- **src/services/writing_services.py** (435 statements)
- **src/easy_mode/phase3/asset_pack.py** (324 statements)
- **src/easy_mode/phase3/ebook_export.py** (307 statements)
- **src/easy_mode/phase3/if_routes.py** (399 statements)
- **src/easy_mode/phase3/media_mix.py** (468 statements)

---

## フェーズ別実装計画

### Phase 1: 基盤インフラのテスト化（Week 1-2）
**目標**: 共通基盤モジュールを 80% 以上に引き上げ

| モジュール | 現状 | 目標 | 推定工数 | 優先度 |
|-----------|------|------|----------|--------|
| src/shared/result.py | 53.7% | 80%+ | 0.5日 | 高 |
| src/shared/circuit_breaker.py | 89% (branch 70%) | 80%+ | 0.5日 | 高 |
| src/shared/resilience_config.py | 83% (branch 75%) | 80%+ | 0.5日 | 高 |
| src/shared/resilient_http.py | 83% (branch 60%) | 80%+ | 1日 | 高 |
| src/shared/retry_policy.py | 100% | 維持 | - | - |
| src/shared/errors.py | 85% | 80%+ | 0.5日 | 中 |
| src/shared/utils/__init__.py | 43.5% | 80%+ | 1日 | 中 |

**アクション**:
- 既存テストの拡充（ブランチカバレッジ重視）
- モック・フィクスチャの整備
- エッジケース（タイムアウト、リトライ上限、サーキットオープン等）の追加

---

### Phase 2: コアエンジン・バックエンド基盤（Week 2-4）
**目標**: エンジン・DB・ワークフロー核心部を 80% 以上に引き上げ

| モジュール群 | 代表ファイル | 現状 | 目標 | 推定工数 | 優先度 |
|-------------|-------------|------|------|----------|--------|
| エンジンコア | engine.py, engine_context.py, engine_critique.py, engine_narrative.py, engine_utils.py | 6-47% | 80%+ | 8日 | **最高** |
| DB層 | database/core.py, database/uow.py, database/repository.py, repositories/* | 14-42% | 80%+ | 10日 | **最高** |
| ワークフロー | workflows/*.py (9ファイル) | 8-48% | 80%+ | 12日 | **最高** |
| サニタイザー | sanitizer.py | 8.5% | 80%+ | 3日 | 高 |
| 観測性 | observability.py, observability/health.py, observability/metrics.py | 29-50% | 80%+ | 3日 | 高 |

**アプローチ**:
1. **Repository層**: インメモリ実装（repo_inmemory.py）を活用した高速ユニットテスト
2. **UoW**: トランザクション境界・ロールバック・ネストトランザクションのテスト
3. **エンジン**: モックLLM・モックRepositoryでの統合テスト
4. **ワークフロー**: LangGraphステート遷移の網羅的テスト

---

### Phase 3: サービス層（Week 4-6）
**目標**: ビジネスロジックサービスを 80% 以上に引き上げ

| モジュール | 現状 | 目標 | 推定工数 | 優先度 |
|-----------|------|------|----------|--------|
| writing_services.py | 10.1% | 80%+ | 5日 | **最高** |
| redis_cache.py | 12.9% | 80%+ | 3日 | **最高** |
| vector_store.py | 17.0% | 80%+ | 3日 | 高 |
| auto_workflow_pipeline.py | ?% (0%可能性) | 80%+ | 3日 | 高 |
| bible_service.py (services) | 9.4% | 80%+ | 2日 | 高 |
| episode_writer.py | 12.3% | 80%+ | 2日 | 高 |
| novel_producer.py | 26.9% | 80%+ | 2日 | 高 |
| erotic関連サービス | 17-51% | 80%+ | 5日 | 中 |
| illustration系サービス | 9-55% | 80%+ | 3日 | 中 |
| LLM関連サービス | 28-33% | 80%+ | 3日 | 中 |

**アプローチ**:
- 依存性注入（dependency-injector）を活用し、外部依存をモック化
- キャッシュ・ベクトルストアは fakeredis / インメモリ実装で高速化
- パイプライン系はステップごとの単体テスト + 統合テスト

---

### Phase 4: エージェント・LLM・EasyMode（Week 6-8）
**目標**: エージェント・LLMクライアント・EasyModeを 80% 以上に引き上げ

| モジュール群 | 代表ファイル | 現状 | 目標 | 推定工数 | 優先度 |
|-------------|-------------|------|------|----------|--------|
| エージェント基盤 | agents/base.py, agents/bible.py, agents/planning.py, agents/plot.py | 8-43% | 80%+ | 5日 | 高 |
| 文章生成エージェント | agents/writing/*.py, agents/context_builder.py | 6-41% | 80%+ | 5日 | 高 |
| エロティック特化 | agents/erotic/*.py, erotic_enhancer.py | 16-77% | 80%+ | 4日 | 中 |
| LLMクライアント | core/llm_clients/*.py, core/llm_gateway.py, llm/model_router.py | 11-21% | 80%+ | 4日 | 高 |
| EasyMode Phase3 | easy_mode/phase3/*.py (4ファイル) | 12-23% | 80%+ | 6日 | 中 |
| EasyMode パイプライン | easy_mode/pipeline.py, spice_guard.py | 15-21% | 80%+ | 3日 | 中 |

**アプローチ**:
- LLM呼び出しは `pytest-mock` / `respx` で完全モック化
- プロンプト構築ロジックの単体テストに集中
- ストリーミング・非同期処理のテストは `pytest-asyncio` で

---

### Phase 5: API・ルーター・フロントエンド連携（Week 8-10）
**目標**: API層・ルーターを 80% 以上に引き上げ

| モジュール群 | 現状 | 目標 | 推定工数 | 優先度 |
|-------------|------|------|----------|--------|
| ルーター (18ファイル) | routers/*.py | 16-71% | 80%+ | 8日 | 高 |
| 認証・認可 | auth.py, rate_limit.py | 25-31% | 80%+ | 2日 | 高 |
| SSE・ストリーミング | sse.py, streaming.py | 6-46% | 80%+ | 2日 | 中 |
| バックグラウンドタスク | background.py, tasks/*.py | 0-31% | 80%+ | 3日 | 中 |
| ヘルスチェック | health/*.py | 0-29% | 80%+ | 1日 | 中 |

**アプローチ**:
- `TestClient` (FastAPI) を活用した契約テスト
- 認証ミドルウェアのモック化
- WebSocket/SSEは統合テストでカバー

---

### Phase 6: ドメイン・モデル・インフラ（Week 10-11）
**目標**: ドメインモデル・インフラ基盤を 80% 以上に引き上げ

| モジュール群 | 現状 | 目標 | 推定工数 | 優先度 |
|-------------|------|------|----------|--------|
| ドメインモデル | domain/*.py, models/*.py | 20-61% | 80%+ | 4日 | 中 |
| インフラAPI | infrastructure/api/*.py | 0-?% | 80%+ | 2日 | 低 |
| カーネル | kernels/*.py (13ファイル) | 0-?% | 80%+ | 4日 | 低 |
| プリセット・プロンプト | presets/*, prompts/* | 18-?% | 80%+ | 2日 | 低 |

---

### Phase 7: E2E・統合・パフォーマンステスト（Week 11-12）
**目標**: 全体統合・回帰防止・カバレッジ最終調整

| 内容 | 推定工数 |
|------|----------|
| 既存E2Eテストの拡充・安定化 | 3日 |
| パフォーマンステストのカバレッジ寄与確認 | 1日 |
| カバレッジ未達モジュールの個別対応 | 4日 |
| CI/CDパイプラインへのカバレッジゲート組み込み | 1日 |
| ドキュメント化・チーム共有 | 1日 |

---

## 実装アプローチ詳細

### 1. テスト戦略の原則
- **ピラミッド型**: Unit (70%) > Integration (20%) > E2E (10%)
- **モックファースト**: 外部依存（DB、Redis、LLM API、HTTP）は全てモック化
- **決定論的テスト**: 乱数・時刻・外部状態を固定化
- **高速実行**: 単体テストは 100ms 以内、統合テストは 1s 以内を目標

### 2. 必要なテストインフラ整備

```python
# tests/conftest.py 追加推奨フィクスチャ
@pytest.fixture
def mock_llm_client():
    """全LLM呼び出しをモック"""
    
@pytest.fixture  
def mock_redis():
    """fakeredis またはインメモリ実装"""
    
@pytest.fixture
def mock_vector_store():
    """インメモリベクトルストア"""
    
@pytest.fixture
def sample_book():
    """テスト用ブックエンティティ"""
    
@pytest.fixture
def sample_chapter():
    """テスト用チャプターエンティティ"""
```

### 3. カバレッジ測定設定（pyproject.toml 追加）

```toml
[tool.pytest.ini_options]
addopts = "-p no:cacheprovider --tb=short --cov=src --cov-fail-under=80 --cov-branch"
asyncio_mode = "auto"

[tool.coverage.run]
source = ["src"]
omit = [
    "*/tests/*",
    "*/migrations/*",
    "*/alembic/*",
    "*/conftest.py",
    "*/__pycache__/*",
]
branch = true
concurrency = ["multiprocessing", "thread", "gevent"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
]
precision = 2
show_missing = true
skip_covered = false

[tool.coverage.html]
directory = "htmlcov"
```

### 4. CI/CD ゲート設定例（GitHub Actions）

```yaml
# .github/workflows/test.yml 抜粋
- name: Run tests with coverage
  run: |
    pytest --cov=src --cov-report=xml --cov-fail-under=80 --cov-branch
    
- name: Upload coverage
  uses: codecov/codecov-action@v3
  with:
    files: ./coverage.xml
    fail_ci_if_error: true
```

---

## リソース見積もり

| フェーズ | 期間 | 工数（人日） | 主担当 |
|----------|------|-------------|--------|
| Phase 1: 基盤インフラ | Week 1-2 | 4 | 1名 |
| Phase 2: コアエンジン・DB | Week 2-4 | 36 | 2名 |
| Phase 3: サービス層 | Week 4-6 | 26 | 2名 |
| Phase 4: エージェント・LLM | Week 6-8 | 27 | 2名 |
| Phase 5: API・ルーター | Week 8-10 | 16 | 1名 |
| Phase 6: ドメイン・インフラ | Week 10-11 | 12 | 1名 |
| Phase 7: E2E・最終調整 | Week 11-12 | 10 | 1名 |
| **合計** | **12週間** | **約131人日** | **2-3名並列** |

---

## リスクと対策

| リスク | 影響度 | 発生確率 | 対策 |
|--------|--------|----------|------|
| 既存テストの冗長性・脆さ | 高 | 高 | 先行リファクタリング週を設ける（Phase 0） |
| モック維持コストの増大 | 中 | 高 | 共通モックファクトリ・フィクスチャで標準化 |
| 非同期・並行処理のテスト困難 | 高 | 中 | `pytest-asyncio`, `anyio`, タイムアウト設定で制御 |
| LLM出力の非決定性 | 中 | 高 | プロンプト構築・パースロジックのみテスト、出力はスナップショット |
| 期間延長 | 高 | 中 | フェーズごとにマイルストーン設定、週次レビュー |

---

## 成功指標（KPI）

| 指標 | 目標 | 測定タイミング |
|------|------|----------------|
| 全体行カバレッジ | ≥ 80% | 各フェーズ終了時 / PRマージ時 |
| 全体ブランチカバレッジ | ≥ 80% | 同上 |
| 0%カバレッジファイル数 | 0 | Phase 2終了時 |
| 新規コードのカバレッジ | ≥ 90% | 常時（CIゲート） |
| テスト実行時間（全体） | < 10分 | CI実行毎 |
| フレーキーテスト率 | < 1% | 週次集計 |

---

## すぐに着手可能な Quick Wins（今週中）

1. **`src/shared/result.py`** (53.7% → 80%+): Result型の unwrap/map/map_err 系メソッドのテスト追加のみで達成可能
2. **`src/shared/circuit_breaker.py`** ブランチカバレッジ 70% → 80%: 例外系ブランチのテスト追加
3. **`src/shared/resilient_http.py`** ブランチカバレッジ 60% → 80%: PUT/DELETE/エラー系パスのテスト追加
4. **`src/shared/utils/__init__.py`** (43.5% → 80%+): TokenUsageTracker, estimate_tokens のテスト追加
5. **`src/backend/server.py`** (79.6% → 80%+): 残り数行のカバーで達成

---

## 次のアクション

1. **Phase 0 (準備)**: 既存テストの整理・共通フィクスチャ整備・カバレッジゲート設定
2. **Phase 1 着手**: shared モジュールから開始（依存が少なく ROI 高い）
3. **並列化**: Phase 2以降はモジュール群ごとに並列実行可能
4. **週次レビュー**: カバレッジ推移の可視化・ボトルネック早期発見