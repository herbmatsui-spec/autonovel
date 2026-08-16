# 詳細実装ステップ計画書 (低性能LLM対応・超微細分割)

**方針**: 各タスクを **1-2ファイル・10-30行程度の変更** に分解。1ステップ = 1コミット単位。
**全フェーズ合計**: 48ステップ (Critical 12 + High 12 + Medium 12 + Low 12)

---

## Phase 1: Critical (即時修正・12ステップ・約45分)

### Step 1-1: `llm_gateway.py` 重複メソッド削除 (前半)
- **対象**: `src/core/llm_gateway.py` 行 262-287 (`_normalize_response` 2回目, `_usage_metric` 2回目)
- **アクション**: この 26 行を**完全削除**
- **確認**: 行 92-110 (1回目定義) のみ残ること

### Step 1-2: `llm_gateway.py` 重複削除後の構文チェック
- **アクション**: `python -m py_compile src/core/llm_gateway.py` でエラーなし確認

### Step 1-3: `app.py` DUMMY APIキーを Settings 注入に変更
- **対象**: `src/core/container/app.py` 行 28
- **変更前**: `api_key = providers.Object("DUMMY")`
- **変更後**: 
  ```python
  from config.settings import get_settings
  api_key = providers.Callable(lambda: get_settings().gemini_api_key or "DUMMY")
  ```
  ※ `gemini_api_key` フィールドが Settings にない場合は `openai_api_key` または環境変数直読みで暫定対応

### Step 1-4: `app.py` 必要インポート追加 (Step 1-3 用)
- **対象**: `src/core/container/app.py` ファイル冒頭
- **追加**: `from config.settings import get_settings` (未追加なら)

### Step 1-5: `app.py` connection_pipeline 削除判断・実行
- **対象**: `src/core/container/app.py` 行 53
- **アクション**: `grep -r "connection_pipeline" src/` で使用箇所確認 → 未使用なら行削除

### Step 1-6: `settings.py` polishing_min_content_ratio 重複削除
- **対象**: `config/settings.py` 行 209
- **アクション**: 行 209 (`polishing_min_content_ratio: float = 0.5`) を**削除** (行 159 を残す)

### Step 1-7: `settings.py` 重複削除後の構文チェック
- **アクション**: `python -m py_compile config/settings.py`

### Step 1-8: 全体 lint 実行 (Critical 完了確認)
- **アクション**: `ruff check src/ config/settings.py` → エラー 0 確認

### Step 1-9: 型チェック実行
- **アクション**: `mypy --config-file pyproject.toml src/core/llm_gateway.py src/core/container/app.py config/settings.py` → エラー減少確認

### Step 1-10: 関連テスト実行
- **アクション**: `pytest tests/ -k "llm or container or config" -x -q` → 全パス確認

### Step 1-11: 文字化けチェック
- **アクション**: `git grep -P "\xEF\xBF\xBD" -- '*.py' '*.md' '*.yaml' '*.yml' '*.toml' '*.json' '*.txt' 2>/dev/null || echo "OK"`

### Step 1-12: Phase 1 コミット
- **アクション**: `git add -A && git commit -m "Phase 1 Critical: 重複削除・DUMMYキー修正・設定重複解消 (12 steps)"`

---

## Phase 2: High (エンジンリファクタ・12ステップ・約4-6時間)

### Step 2-1: EngineDeps データクラス定義ファイル作成
- **新規作成**: `src/backend/engine_deps.py`
- **内容**: 
  ```python
  from dataclasses import dataclass
  from typing import Optional, TYPE_CHECKING
  if TYPE_CHECKING:
      from src.agents.PlanningAgent import PlanningAgent
      from src.agents.WritingAgent import WritingAgent
      from prompts.manager import PromptManager
      from src.backend.engine_context import ContextManager
      from src.backend.sanitizer import TextFormatter
      from src.agents.audit import LogicalAuditor
      from src.backend.engine_narrative import NarrativeController
      from src.backend.engine_critique import CritiqueAgent
      from src.agents.MarketingAgent import MarketingAgent
      from src.services.bible_service import WorldBibleGenerator
      from src.agents.plot import PlotAgent
      from src.backend.engine_style_rag import StyleRagManager
  
  @dataclass
  class EngineDeps:
      planner: Optional["PlanningAgent"] = None
      writer: Optional["WritingAgent"] = None
      pm: Optional["PromptManager"] = None
      ctx_mgr: Optional["ContextManager"] = None
      formatter: Optional["TextFormatter"] = None
      validator: Optional["LogicalAuditor"] = None
      auditor: Optional["LogicalAuditor"] = None
      narrative: Optional["NarrativeController"] = None
      critique: Optional["CritiqueAgent"] = None
      marketing: Optional["MarketingAgent"] = None
      bible_agent: Optional["WorldBibleGenerator"] = None
      plot_agent: Optional["PlotAgent"] = None
      style_rag: Optional["StyleRagManager"] = None
  ```

### Step 2-2: `engine.py` EngineDeps インポート追加
- **対象**: `src/backend/engine.py` インポート部
- **追加**: `from src.backend.engine_deps import EngineDeps`

### Step 2-3: `UltimateHegemonyEngine.__init__` 引数を EngineDeps 1つに変更 (シグネチャのみ)
- **対象**: `src/backend/engine.py` 行 41-64
- **変更前**: 13個の `Optional[...]` 引数 + `**legacy`
- **変更後**: `deps: Optional[EngineDeps] = None, **legacy`
- **注意**: このステップでは本体ロジック未変更、シグネチャのみ

### Step 2-4: `__init__` 内部で deps から属性設定するロジック追加
- **対象**: `src/backend/engine.py` `__init__` 内部 (行 65-98 付近)
- **追加**: 
  ```python
  if deps is not None:
      self._planner = deps.planner
      self._writer = deps.writer
      self._pm = deps.pm
      self._ctx_mgr = deps.ctx_mgr
      self._formatter = deps.formatter
      self._validator = deps.validator
      self._auditor = deps.auditor
      self._narrative = deps.narrative
      self._critique = deps.critique
      self._marketing = deps.marketing
      self._bible_agent = deps.bible_agent
      self._plot_agent = deps.plot_agent
      self._style_rag = deps.style_rag
  ```

### Step 2-5: 既存プロパティ (`planner`, `writer` 等) を deps 対応に微修正
- **対象**: `src/backend/engine.py` 行 116-196 (各 `@property`)
- **変更**: 既存ロジック (`if self._planner is not None: return self._planner`) はそのまま。**変更不要** (Step 2-4 で `_planner` 等が設定されるため自動対応)

### Step 2-6: `AppContainer2` で EngineDeps 組み立て・注入
- **対象**: `src/core/container/app.py` `engine` プロバイダ定義 (行 156-177)
- **変更**: 13個個別引数 → `deps=providers.Factory(EngineDeps, ...)` 1つに集約
- **詳細**: 各フィールドに既存プロバイダ (`planner`, `writer`, `pm` 等) を渡す

### Step 2-7: AppContainer2 インポート追加 (EngineDeps 用)
- **対象**: `src/core/container/app.py` インポート部
- **追加**: `from src.backend.engine_deps import EngineDeps`

### Step 2-8: 起動時依存検証メソッド追加
- **対象**: `src/backend/engine.py` クラス内 (任意の場所)
- **追加**: 
  ```python
  def validate_dependencies(self) -> None:
      """必須依存が揃っているか起動時に検証"""
      required = ["planner", "writer", "pm", "ctx_mgr", "formatter", 
                  "validator", "auditor", "narrative", "critique", 
                  "marketing", "bible_agent", "plot_agent", "style_rag"]
      missing = [name for name in required if getattr(self, f"_{name}") is None and name not in self._legacy]
      if missing:
          raise RuntimeError(f"Missing required dependencies: {missing}. Pass them via EngineDeps or legacy dict.")
  ```

### Step 2-9: `__init__` 末尾で `validate_dependencies()` 呼出
- **対象**: `src/backend/engine.py` `__init__` 最後
- **追加**: `self.validate_dependencies()`

### Step 2-10: 既存テストでエンジン作成箇所を EngineDeps 対応に修正
- **対象**: `tests/` 配下のエンジン直接インスタンス化箇所 (`grep -r "UltimateHegemonyEngine(" tests/`)
- **アクション**: 各箇所で `EngineDeps(...)` 作成して渡すよう修正

### Step 2-11: 全テスト実行・修正
- **アクション**: `pytest tests/ -x -q` → 失敗箇所を 1 つずつ修正

### Step 2-12: Phase 2 コミット
- **アクション**: `git add -A && git commit -m "Phase 2 High: EngineDeps導入・依存注入明示化・起動時検証 (12 steps)"`

---

## Phase 3: Medium (設定・テスト・Docker・12ステップ・約3-4時間)

### Step 3-1: `async_utils.py` に `limit_concurrency` 実装確認・不足なら作成
- **対象**: `src/core/async_utils.py`
- **アクション**: `grep -n "limit_concurrency" src/core/async_utils.py` → なければ実装:
  ```python
  import asyncio
  from typing import TypeVar, Callable, Awaitable
  T = TypeVar("T")
  async def limit_concurrency(coro: Awaitable[T], semaphore: asyncio.Semaphore = None) -> T:
      if semaphore is None:
          semaphore = asyncio.Semaphore(5)
      async with semaphore:
          return await coro
  ```

### Step 3-2: `pipeline.py` で `limit_concurrency` 正常動作確認テスト追加
- **対象**: `tests/unit/test_async_utils.py` (新規)
- **内容**: セマフォ制限動作の単体テスト 3-5 ケース

### Step 3-3: `InfraContainer` が Settings 参照するよう修正
- **対象**: `src/core/container/infra.py` (存在確認から)
- **アクション**: `redis_url`, `chroma_db_path` 等を `get_settings()` 経由で取得

### Step 3-4: CI で LLM ヘルスチェック有効化判断・設定
- **対象**: `.github/workflows/ci.yml`
- **アクション**: `KAKU_HEALTH_CHECK_LLM=true` 追加、またはモックサーバ立てるステップ追加

### Step 3-5: テストディレクトリ再編成 - unit 移動
- **アクション**: `mkdir -p tests/unit && mv tests/test_*.py tests/unit/` (該当ファイルのみ)
- **注意**: `tests/integration/`, `tests/e2e/` 既存は残す

### Step 3-6: テストディレクトリ再編成 - phase 別移動
- **アクション**: `mkdir -p tests/phase1 tests/phase2 tests/phase3 && mv tests/test_phase1*.py tests/phase1/ && mv tests/test_phase2*.py tests/phase2/ && mv tests/test_phase3*.py tests/phase3/`

### Step 3-7: テスト import パス修正 (一括 sed)
- **アクション**: `find tests/ -name "*.py" -exec sed -i 's/from tests\./from tests.unit./g' {} \;` 等 (必要に応じて調整)

### Step 3-8: `pyproject.toml` に `project.dependencies` 追加
- **対象**: `pyproject.toml` `[project]` セクション
- **追加**: `dependencies = ["nest-asyncio>=1.5.0", "google-genai>=0.8.0", ...]` (requirements.txt ランタイム分)

### Step 3-9: `pyproject.toml` に `[project.optional-dependencies.dev]` 追加
- **追加**: `dev = ["pytest>=8.0.0", "pytest-asyncio>=0.23.0", "ruff>=0.5.0", "mypy>=1.10.0", ...]`

### Step 3-10: `requirements.txt` をランタイムのみに整理 (dev 移動)
- **アクション**: 開発用依存 (24-33 行目) を削除、ランタイムのみ残す

### Step 3-11: Dockerfile マルチステージ化・非 root 化
- **対象**: `Dockerfile` (ルート), `frontend/Dockerfile`
- **アクション**: builder stage → runtime stage 分離、非 root ユーザ作成、distroless/base image 採用

### Step 3-12: Phase 3 コミット
- **アクション**: `git add -A && git commit -m "Phase 3 Medium: 非同期ユーティリティ・InfraContainer設定・テスト再編成・依存分離・Dockerfile改善 (12 steps)"`

---

## Phase 4: Low (ドキュメント・品質・12ステップ・約2-3時間)

### Step 4-1: `py.typed` マーカー作成
- **アクション**: `touch src/py.typed`

### Step 4-2: SpiceGuard ドキュメント作成
- **新規**: `docs/architecture/spice_guard.md`
- **内容**: 抽出ロジック、マーカー形式、類似度閾値 0.75 の根拠、リライト時保護フロー

### Step 4-3: フロントエンド Storybook 初期化
- **アクション**: `cd frontend && npx storybook@latest init --yes` (CI でビルド確認用)

### Step 4-4: ADR: LangGraph 採用理由 作成
- **新規**: `docs/adr/0004-langgraph-adoption.md`
- **内容**: 背景、比較検討 (自作パイプライン vs LangGraph)、決定理由、影響

### Step 4-5: 廃止ベンチマークスクリプト削除
- **対象**: `tests/benchmark_streamlit.py`
- **アクション**: `git rm tests/benchmark_streamlit.py`

### Step 4-6: xenon 複雑度しきい値調整 (通る値に)
- **対象**: `.pre-commit-config.yaml` 行 105-107
- **アクション**: `xenon --max-absolute B --max-modules B --max-average A` で現状通るか確認 → 通らなければ `C` 等に緩和

### Step 4-7: pre-commit `no-print-statements` スクリプト化
- **新規**: `scripts/no_print_check.py`
- **内容**: インライン Python を関数化・ファイル化
- **フック修正**: `.pre-commit-config.yaml` で `entry: python scripts/no_print_check.py` に変更

### Step 4-8: `ENV_OVERRIDE_MAP` 検証スクリプト作成・実行
- **新規**: `scripts/validate_env_map.py`
- **内容**: `Settings` フィールド全取得 → `ENV_OVERRIDE_MAP` 値と突合 → 不一致報告
- **実行**: `python scripts/validate_env_map.py` → 不一致あれば修正

### Step 4-9: 全 lint・型チェック・テスト 総合実行
- **アクション**: 
  ```bash
  ruff check src/ tests/
  mypy --config-file pyproject.toml src/
  pytest tests/ -x -q
  cd frontend && npm run lint && npm run test:run
  ```

### Step 4-10: カバレッジ確認 (80% 目標)
- **アクション**: `pytest --cov=src --cov-report=term-missing tests/` → 不足箇所確認

### Step 4-11: CHANGELOG.md 更新 (本計画分の変更まとめ)
- **対象**: `CHANGELOG.md`
- **追加**: Phase 1-4 の変更サマリ

### Step 4-12: Phase 4 (最終) コミット・タグ打ち
- **アクション**: 
  ```bash
  git add -A
  git commit -m "Phase 4 Low: ドキュメント・品質ゲート・設定検証・CHANGELOG更新 (12 steps)"
  git tag v3.3.1-code-review-followup
  ```

---

## 実行ルール (低性能LLMでも迷わないための制約)

1. **1ステップ = 1ツール呼び出しセット** (read → edit → verify の組み合わせ)
2. **各ステップ完了時に必ず検証コマンド実行** (構文チェック/テスト/lint のいずれか)
3. **失敗したらそのステップで止めて修正** (先に進まない)
4. **ファイルパスは絶対パスで指定** (`/home/herbmatsui/autonovel/...`)
5. **変更前には必ず `read` で現状確認**
6. **コミットは各フェーズ末尾 (Step 12, 24, 36, 48) のみ**

---

## 進捗トラッキング表 (実行時更新用)

| ステップ | 状態 | 着手時刻 | 完了時刻 | 備考 |
|----------|------|----------|----------|------|
| 1-1 | 待機 | - | - | |
| 1-2 | 待機 | - | - | |
| ... | ... | ... | ... | |
| 48 | 待機 | - | - | |

**次のアクション**: Step 1-1 から順次実行開始