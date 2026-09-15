# P7: テストカバレッジ80%引き上げ詳細実装計画書

**作成日**: 2026-09-14
**対象**: AutoNovel v4.9.3（e:/hhh）
**目標**: ユニットテストカバレッジ 24.05% → **80%以上**
**前提**: 2026-09-14 時点の実測値（coverage.json / tests/unit --import-mode=importlib）

---

## Part 1: 現状と目標の定量ギャップ

| 指標 | 値 |
|---|---|
| 現在のラインカバレッジ | **24.05%**（covered 15,110 / 49,543 行） |
| 80%到達に必要な追加カバー行 | **約 24,524 行** |
| 既存ユニットテスト数 | 2,234 件 |
| 0%カバレッジファイル | 80 ファイル（未カバー 3,060 行） |
| 1〜49%カバレッジファイル | 約 350 ファイル（未カバー 30,077 行） |

**結論**: 80%到達には「既存低カバレッジファイルの押し上げ」が主体。0%ファイルだけでは不十分（3,060行 = 12.4%ポイント分）であり、**1〜49%帯の大きなファイル（services/agents/backend）を50〜70%まで押し上げる**ことが必須。

---

## Part 2: カテゴリ別の未カバー行と攻略優先度

| カテゴリ | 未カバー行 | 全体行 | 優先度 | 理由 |
|---|---|---|---|---|
| services | **12,343** | 15,769 | ★★★ | 最大の山。純粋ロジックが多くテスト容易 |
| agents | **6,005** | 7,370 | ★★★ | モックでLLMを切ればユニットテスト可能 |
| backend/other | **3,232** | 4,377 | ★★ | engine系・observability系が0% |
| backend/routers | **2,658** | 3,710 | ★★ | TestClient + モックUoWで機械的にカバー可 |
| domain | **1,466** | 3,022 | ★★ | P6で300テスト追加済み、残りはdomain_services残部 |
| backend/tasks | **1,464** | 1,868 | ★★ | DAG scheduler系は既存テストあり、残部を補完 |
| easy_mode | **1,375** | 1,780 | ★ | phase3 4ファイルの残部 |
| backend/workflows | **1,205** | 1,506 | ★★ | LangGraphノードはモック容易 |
| infrastructure | **1,096** | 1,721 | ★ | repositoryパターンでモック容易 |
| core | **847** | 1,503 | ★★ | async_utils/plugin系 |
| backend/database | **843** | 1,744 | ★ | テスト既存、残部補完 |
| models | **650** | 2,514 | ★ | pydanticモデル、軽量 |
| llm | **384** | 492 | ★★ | resilient_gateway等 |
| engine | **183** | 199 | ★ | prompts/erotic_specialistのみ |
| config | **126** | 280 | - | 小規模 |

---

## Part 3: 攻略戦略（3段階）

### 戦略の核心

1. **「1テスト = 平均12行カバー」換算**で、80%到達に必要なテスト数は **約 2,050 件**
2. ただし既存2,234件の低カバレッジ対象を**押し上げ方式**（不足行を集中補完）にすることで、新規テストは **約 1,200〜1,500 件**に圧縮可能
3. 1ステップ = 1カテゴリの主要ファイル群を「50〜70%押し上げ」し、段階的に25%→40%→55%→65%→80%と測定確認

### カバレッジの押し上げ計算

| 段階 | カバー行 | カバレッジ |
|---|---|---|
| 現在 | 15,110 | 24.05% |
| Step A完了（services押し上げ） | +8,000 | **40.2%** |
| Step B完了（agents押し上げ） | +4,500 | **49.3%** |
| Step C完了（backend押し上げ） | +5,500 | **60.4%** |
| Step D完了（domain/easy_mode/workflows） | +4,000 | **68.5%** |
| Step E完了（core/infrastructure/models/llm） | +4,200 | **77.0%** |
| Step F完了（残り微調整） | +1,600 | **80.2%** ✅ |

---

## Part 4: ステップ別詳細実装計画

### Step A: services系押し上げ（未カバー 12,343行 → 4,300行削減）

**目標**: services カテゴリ 22%→72%、全体 +8,000行

| ファイル | 現状 | 未カバー | テスト追加数 | 押上げ後目標 |
|---|---|---|---|---|
| `src/services/vector_store.py` | 0% | 624 | 40 | 65%（ChromaFacade/DefaultVectorStore/get_default_store/pgvector_adapter） |
| `src/services/age_client.py` | 9.8% | 525 | 35 | 60%（HTTPモック、エラー経路） |
| `src/services/book_score_service.py` | 6.3% | 483 | 32 | 60%（スコア集計・モックUoW） |
| `src/services/writing_services.py` | 8.7% | 384 | 25 | 60%（コンテキスト構築・パース） |
| `src/services/reflective_rag.py` | 13.6% | 324 | 22 | 60%（リフレクション判定） |
| `src/services/pipeline_steps.py` | 7.0% | 323 | 22 | 55%（各ステップの正常系+異常系） |
| `src/services/rag_service.py` | 13.2% | 319 | 21 | 60%（検索・フィルタ） |
| `src/services/exporters/base.py` | 13.1% | 302 | 20 | 60%（エクスポート基底） |
| `src/services/redis_cache.py` | 12.9% | 299 | 20 | 60%（fakeredisモック） |
| `src/services/bible_service.py` | 8.3% | 243 | 16 | 60% |
| `src/services/anti_ai/detectors.py` | 10.3% | 236 | 16 | 60% |
| `src/services/graphrag_sync_service.py` | 0% | 106 | 8 | 55% |
| `src/services/conflict_report_service.py` | 0% | 104 | 7 | 55% |
| `src/services/marketing.py` | 0% | 76 | 5 | 55% |
| `src/services/cadence/*`（3ファイル） | 0% | 187 | 13 | 55% |
| `src/services/hook_diagnoser.py` | 0% | 35 | 3 | 55% |
| `src/services/episode_context.py` | 0% | 33 | 3 | 55% |
| `src/services/audit_service.py` | 0% | 27 | 2 | 55% |
| その他小規模 services 0%群 | 0% | 約180 | 12 | 55% |
| **合計** | | **約 4,866** | **約 296** | |

**実装パターン**:
- LLM依存は `tests/mocks/llm_adapter.MockLLMAdapter` を注入
- DB依存は `AsyncMock` リポジトリ or `real_db_manager` フィクスチャ（tests/conftest.py）
- 外部HTTPは `respx`（httpxモック）または `AsyncMock` クライアント

### Step B: agents系押し上げ（未カバー 6,005行 → 1,500行削減）

**目標**: agents カテゴリ 18%→70%、全体 +4,500行

| ファイル | 現状 | 未カバー | テスト追加数 |
|---|---|---|---|
| `src/agents/erotic/continuity.py` | 12.8% | 502 | 34 |
| `src/agents/audit.py` | 8.9% | 403 | 27 |
| `src/agents/enrichment_agent.py` | 5.2% | 393 | 26 |
| `src/agents/context_builder_agent.py` | 5.2% | 392 | 26 |
| `src/agents/orchestrator.py` | 9.2% | 341 | 23 |
| `src/agents/erotic/filter.py` | 18.1% | 228 | 15 |
| `src/agents/enrichment/sensory.py` | 7.9% | 212 | 14 |
| `src/agents/illustration_agent.py` | 8.8% | 208 | 14 |
| `src/agents/writing/episode_writer.py` | 0% | 56 | 4 |
| `src/agents/state_validator.py` | 0% | 29 | 2 |
| `src/agents/early_entertainment_checker.py` | 0% | 24 | 2 |
| その他小規模 agents | 0% | 約 80 | 6 |
| **合計** | | **約 2,568** | **約 193** |

### Step C: backend系押し上げ（未カバー 7,354行 → 1,900行削減）

**目標**: backend全体 30%→65%、全体 +5,500行

| ファイル | 現状 | 未カバー | テスト追加数 |
|---|---|---|---|
| `src/backend/routers/branches.py` | 11.7% | 461 | 30 |
| `src/backend/sanitizer.py` | 8.5% | 425 | 28 |
| `src/backend/engine_context.py` | 6.1% | 241 | 16 |
| `src/backend/observability/metrics.py` | 0% | 182 | 12 |
| `src/backend/routers/orchestrated.py` | 0% | 112 | 8 |
| `src/backend/engine.py` | 0% | 120 | 8 |
| `src/backend/engine_plot.py` | 0% | 97 | 7 |
| `src/backend/tasks/illustration_tasks.py` | 0% | 58 | 4 |
| `src/backend/routers/prompt_compare.py` | 0% | 53 | 4 |
| `src/backend/workflows/quality_metrics.py` | 0% | 53 | 4 |
| `src/backend/checkpoint_saver.py` | 0% | 51 | 4 |
| `src/backend/observability.py` | 0% | 50 | 4 |
| `src/backend/llm_client.py` | 0% | 46 | 3 |
| `src/backend/routers/hooks.py` | 0% | 46 | 3 |
| `src/backend/routers/collab.py` | 0% | 60 | 4 |
| `src/backend/entertainment_loop.py` | 0% | 39 | 3 |
| `src/backend/tasks/generation_tasks.py` | 9.4% | 235 | 16 |
| `src/backend/workflows/writing_langgraph.py` | 9.1% | 358 | 24 |
| `src/backend/multimedia_service.py` | 12.9% | 230 | 15 |
| `src/backend/database/core.py` | 22.0% | 201 | 13 |
| `src/backend/database/social_repository.py` | 8.2% | 221 | 15 |
| **合計** | | **約 3,547** | **約 229** |

**routers系の実装パターン**（既存 `tests/integration/test_critical_routers_auth.py` を踏襲）:
```python
from fastapi.testclient import TestClient
# AUTH_DISABLED でテストサーバを構築し、UoW/サービスを DI でモック
# 正常系 1 + 認証エラー 1 + バリデーションエラー 1 + 業務エラー 1 を各エンドポイントに
```

### Step D: domain/easy_mode/workflows押し上げ（未カバー 4,046行 → 1,500行削減）

| 対象 | 未カバー | テスト追加数 |
|---|---|---|
| `src/domain/domain_services/*`（残部） | 約 600 | 40 |
| `src/domain/chapter.py` / `character.py` 等旧VO | 46 | 4 |
| `src/easy_mode/phase3/media_mix.py` | 399 | 27 |
| `src/easy_mode/phase3/if_routes.py` | 316 | 21 |
| `src/easy_mode/phase3/asset_pack.py` | 285 | 19 |
| `src/easy_mode/phase3/ebook_export.py` | 256 | 17 |
| `src/backend/workflows/*`（graph_state等） | 約 800 | 53 |
| **合計** | **約 2,700** | **約 181** |

### Step E: core/infrastructure/models/llm押し上げ（未カバー 2,977行 → 1,800行削減）

| 対象 | 未カバー | テスト追加数 |
|---|---|---|
| `src/core/async_utils.py` | 45 | 3 |
| `src/core/system_plugin_loader.py` | 54 | 4 |
| `src/core/plugin_loader.py` | 37 | 3 |
| `src/core/executor_manager.py` | 29 | 2 |
| `src/core/*` その他 | 約 480 | 32 |
| `src/infrastructure/repositories/*` | 約 500 | 34 |
| `src/infrastructure/*` その他 | 約 300 | 20 |
| `src/models/plot.py` | 215 | 14 |
| `src/models/*` その他 | 約 300 | 20 |
| `src/llm/resilient_gateway.py` | 209 | 14 |
| `src/llm/*` その他 | 約 150 | 10 |
| **合計** | **約 2,300** | **約 156** |

### Step F: 最終調整（+1,600行）

- 残存 0%ファイルの小規模群（各3〜30行 × 約40ファイル）→ 約 100 テスト
- 50〜79%帯ファイルの残分支線（計算: 1,183行）→ 約 80 テスト

---

## Part 5: スケジュールと成果物

| ステップ | 新規テスト数 | 累計 | カバレッジ見込み | 検証コマンド |
|---|---|---|---|---|
| Step A | ~296 | 296 | 40% | `pytest tests/unit --cov=src --cov-report=term` |
| Step B | ~193 | 489 | 49% | 同上 |
| Step C | ~229 | 718 | 60% | 同上 |
| Step D | ~181 | 899 | 68% | 同上 |
| Step E | ~156 | 1,055 | 77% | 同上 |
| Step F | ~180 | **1,235** | **80%+** | 同上 + `--cov-fail-under=80` |

**成果物**:
1. 新規テストファイル約 60〜80 本（`tests/unit/services/`, `tests/unit/agents/`, `tests/unit/routers/` 等）
2. 各ステップ完了時の coverage.json スナップショット
3. 最終的に `pyproject.toml` の `--cov-fail-under` を 35 → 80 に更新

**受け入れ基準**:
- [ ] 全ステップ完了後、ラインカバレッジ 80% 以上
- [ ] 既存 2,234 テスト + 新規テストが全て成功
- [ ] `--cov-fail-under=80` を CI ゲートとして設定
- [ ] 0%ファイル数が 80 → 20 以下

---

## Part 6: 実装時の共通注意事項

1. **環境**: Python 3.14.0 / pytest 9.0.3 / `--import-mode=importlib` 必須（同名テストモジュール衝突回避）
2. **__pycache__**: 実行前に `scripts/tmp_clear_pycache.py` を実行（import mismatch 予防）
3. **LLMモック**: `tests/mocks/llm_adapter.py` の MockLLMAdapter / MockLLMAdapterファクトリを第一選択とする
4. **DBモック**: 軽量ユニットは `AsyncMock` リポジトリ、統合系は `real_db_manager`（SQLite一時DB）
5. **chromadb未導入環境**: `HAS_CHROMA=False` 前提のフォールバック経路を必ずテスト
6. **1ファイルあたりのテスト配置規約**: 対象モジュールのパスに対応する tests 配下（例: `src/services/foo.py` → `tests/unit/services/test_foo.py`）
7. **禁止事項**: 実コード（src/）へのカバレッジ向上目的の改変は原則禁止（テストで寄せる）。ただしテスト不能なデッドコードが判明した場合は omit 追加で対処

---

## Part 7: リスクと緩和策

| リスク | 影響 | 緩和策 |
|---|---|---|
| 大規模ファイル（vector_store.py 1,428行等）のテスト工数肥大 | Step A遅延 | ファサード+主要メソッドに絞り、内部詳細は統合テストで担保 |
| routers テストでのDI複雑性 | Step C遅延 | 既存 conftest フィクスチャ（auth/mocked uow）を再利用 |
| LLM依存エージェントの網羅困難 | Step B遅延 | MockLLMAdapter の出力パターンを拡張（正常/JSON壊れ/タイムアウト） |
| カバレッジ計測の遅さ（--cov付きで約30秒） | 検証回数 | カテゴリ単位で `--cov=src/services` 等に絞って高速検証 |
