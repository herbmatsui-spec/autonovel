# 覇権エンジン 第5次リファクタリング 72ステップ実装計画書

> 作成日: 2026-07-30
> 基盤: `proposals/refactoring_proposal_5.md`
> 対象: 低性能LLMでも実装可能な最小ステップ分解

---

## 概要

| フェーズ | ステップ範囲 | 対象提案 | 所要日数目安 |
|----------|-------------|----------|-------------|
| Phase 1 | Step 1-9 | #3 デッドコード一掃 | 0.5日 |
| Phase 2 | Step 10-21 | #4 グローバルSingleton解消 + #5 `__getattr__`一掃 | 1日 |
| Phase 3 | Step 22-35 | #2 二重DIコンテナ統合 | 1日 |
| Phase 4 | Step 36-57 | #1 UltimateHegemonyEngine分解 | 2日 |
| Phase 5 | Step 58-72 | #6 三層モデルflatten + #7 kernels分離 + #8 Streamlit分離 | 2日 |

**合計: 72ステップ / 約6.5日**

---

## Phase 1: デッドコード一掃 (Step 1-9)

### Step 1: `src/database/uow.py` の内容確認と削除
**対象ファイル:** `src/database/uow.py`
**アクション:**
1. ファイルを読み、中身が空または `src/backend/database/uow.py` への re-export のみか確認
2. `grep -r "from src.database.uow" src/ --include="*.py"` で参照箇所を確認
3. 参照がなければ削除 (`rm src/database/uow.py`)
4. `src/database/__init__.py` が存在すれば合わせて削除

**完了条件:** `src/database/` ディレクトリが消滅、grep でヒット0件

---

### Step 2: ルート `services/errors.py` の削除
**対象ファイル:** `services/errors.py`
**アクション:**
1. `grep -r "from services.errors import" src/ --include="*.py"` で参照箇所確認
2. 全参照が `src.services.errors` に向けられるよう修正（あれば）
3. `rm services/errors.py`
4. `rm services/tracing_service.py` （Step 3と合わせて）

**完了条件:** ルート `services/` ディレクトリが空または消滅

---

### Step 3: ルート `services/tracing_service.py` の削除
**対象ファイル:** `services/tracing_service.py`
**アクション:**
1. `grep -r "from services.tracing_service" src/ --include="*.py"` で参照確認
2. `src/services/tracing_service.py` に実体があることを確認
3. ルートファイルを削除

---

### Step 4: ルート `.db-shm`, `.db-wal`, `huey.db` ファイルの Git から削除
**対象:** Git 管理下の生成物
**アクション:**
```bash
git rm --cached src/backend/kaku_hegemony_v2\ \(1\).db-shm
git rm --cached src/backend/kaku_hegemony_v2_huey.db
git rm --cached src/backend/kaku_hegemony_v2.db-shm
git rm --cached src/backend/kaku_hegemony_v2.db-wal
git rm --cached huey.db  # ルートにある場合
git rm --cached .coverage  # ルートにある場合
```
**確認:** `git status` で staged 削除状態になっていること

---

### Step 5: `.gitignore` に生成物パターンを追加
**対象ファイル:** `.gitignore`
**追加内容:**
```
# Database artifacts
*.db-shm
*.db-wal
*.db-journal
huey.db

# Coverage
.coverage
coverage.xml
htmlcov/

# Python cache (既存にない場合)
__pycache__/
*.py[cod]
```
**確認:** `git status` で上記ファイルが untracked 扱いになっていること

---

### Step 6: 孤立テスト6ファイルの移設先決定と移動
**対象ファイル:**
- `test_api.py` → `tests/integration/test_api.py`
- `test_db.py` → `tests/integration/test_db.py`
- `test_db_lock.py` → `tests/integration/test_db_lock.py`
- `test_exact_scenario.py` → `tests/e2e/test_exact_scenario.py`
- `test_manual_sharp_edge.py` → `tests/e2e/test_manual_sharp_edge.py`
- `test_new_sharp_edge.py` → `tests/e2e/test_new_sharp_edge.py`

**アクション:**
1. `tests/integration/` と `tests/e2e/` ディレクトリが存在するか確認（なければ作成）
2. `git mv test_api.py tests/integration/test_api.py` 等で移動（履歴保持）
3. 各ファイル内の import パスが崩れていないか確認（相対importでないため多分OK）

---

### Step 7: 移設テストファイルの import 修正・pytest 収集確認
**アクション:**
1. `pytest tests/integration/test_api.py --collect-only` 等で収集確認
2. 失敗する import があれば修正（`sys.path` 追加や相対import化）
3. `pytest tests/integration/ tests/e2e/ -q` で全件実行・失敗数確認

**完了条件:** 収集エラー0件（失敗は許容、収集だけ通ればOK）

---

### Step 8: `src/models/__init__.py` の `plot` import 修正
**対象ファイル:** `src/models/__init__.py`
**現状:** `from src.models.plot import *` だが `src/models/plot.py` が存在しない
**アクション:**
1. `ls src/models/plot.py` で存在確認（ないはず）
2. `ls models/plot.py` でルートにあることを確認
3. 修正案A: `src/models/plot.py` にコピー・配置（推奨）
   ```bash
   cp models/plot.py src/models/plot.py
   ```
4. 修正案B: import パスを `from models.plot import *` に変更（sys.path 依存になるため非推奨）
5. `python -c "from src.models import PlotEpisode; print('OK')"`

---

### Step 9: Phase 1 完了確認・全体テスト実行
**アクション:**
```bash
pytest tests/unit -q --tb=no -x
pytest tests/integration -q --tb=no -x
git status  # 不要ファイルが残っていないか確認
```
**完了条件:** 既存テストが Phase 1 前と同等以上に通る（新規失敗なし）

---

## Phase 2: グローバルSingleton解消 + `__getattr__`一掃 (Step 10-21)

### Step 10: `TraceContext` を `contextvars` 化
**対象ファイル:** `src/core/observability.py`
**変更内容:**
```python
# 変更前
_current_trace_id: Optional[str] = None

@classmethod
def get_trace_id(cls) -> str:
    if cls._current_trace_id is None:
        cls._current_trace_id = str(uuid.uuid4())
    return cls._current_trace_id

# 変更後
import contextvars
_current_trace_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("_current_trace_id", default=None)

@classmethod
def get_trace_id(cls) -> str:
    trace_id = cls._current_trace_id.get()
    if trace_id is None:
        trace_id = str(uuid.uuid4())
        cls._current_trace_id.set(trace_id)
    return trace_id

@classmethod
def set_trace_id(cls, trace_id: str):
    cls._current_trace_id.set(trace_id)

@classmethod
def clear(cls):
    cls._current_trace_id.set(None)
```
**テスト:** `pytest tests/test_trace_context.py -v`

---

### Step 11: `TraceContext` 変更の動作確認テスト追加
**対象ファイル:** `tests/test_trace_context.py`
**追加テストケース:**
- 非同期タスク間で trace_id が独立していること
- `set_trace_id` / `clear` が context ごとに効くこと

---

### Step 12: `_GLOBAL_DB_MANAGER` を DI コンテナ経由に切替（段階的）
**対象ファイル:** `src/backend/database/core.py`
**方針:** グローバル変数は残すが、取得時に DI コンテナ優先にする
```python
# get_db_manager() 内部
def get_db_manager() -> DatabaseManager:
    global _GLOBAL_DB_MANAGER
    if _GLOBAL_DB_MANAGER is not None:
        return _GLOBAL_DB_MANAGER
    # DIコンテナから取得を試みる
    try:
        from src.core.container import InfraContainer
        return InfraContainer.db()
    except Exception:
        pass
    # フォールバック: 従来通り生成
    manager = DatabaseManager(DATABASE_URL)
    _GLOBAL_DB_MANAGER = manager
    return manager
```
**理由:** 即座に全コードを DI 経由に変えると破壊的変更になるため、互換レイヤーを挟む

---

### Step 13: `set_db_manager` を DI コンテナ設定に委譲
**対象ファイル:** `src/backend/database/core.py`
**変更:** `set_db_manager` 内で `InfraContainer.db.override(manager)` も呼ぶよう拡張

---

### Step 14: `PluginLoader._instance` シングルトン削除・スタティック化
**対象ファイル:** `src/core/plugin_loader.py`
**変更:**
- `_instance` クラス変数削除
- `get_instance()` → `load_all_plugins()` というスタティックメソッドに変更
- 呼び出し側（`src/backend/server.py` 等）を `PluginLoader.load_all_plugins()` に修正

---

### Step 15: `ConfigManager._instance` 参照箇所の洗い出しと DI 移行
**アクション:**
1. `grep -r "ConfigManager._instance" src/ --include="*.py"`
2. `grep -r "from config.settings import ConfigManager" src/ --include="*.py"`
3. 該当箇所を `GlobalConfigModel.load()` または DI コンテナの `config` プロバイダ経由に置換

---

### Step 16: `EngineService._instance` 参照箇所の洗い出しと DI 移行
**アクション:**
1. `grep -r "EngineService._instance" src/ --include="*.py"`
2. 同様に DI コンテナ経由に変更

---

### Step 17: `PlotEpisode.__getattr__` を `@property` に置換
**対象ファイル:** `models/plot.py` (または `src/models/plot.py` Step 8 で配置済み)
**変更内容:** `PlotEpisode` クラス内の `__getattr__` メソッド（409行目付近）を削除し、以下を追加:
```python
@property
def tension(self) -> int:
    return self.analytics.tension

@property
def catharsis(self) -> int:
    return self.analytics.catharsis

@property
def tension_delta(self) -> int:
    return self.analytics.tension_delta

# ... analytics, foreshadowing の主要フィールド分同様に追加

@property
def self_critique(self) -> str:
    return self.lite_model_director_notes
```
**注意:** `extra_engines` へのフォールバックは削除（動的属性アクセスを許さない）

---

### Step 18: `DatabaseConnectionWrapper.__getattr__` を明示ラップに置換
**対象ファイル:** `src/backend/database/core.py` (94行目付近)
**変更:** `__getattr__` 削除、必要なメソッド（`cursor`, `commit`, `rollback`, `close` 等）を明示的に定義

---

### Step 19: `UltimateHegemonyEngine` のエイリアス属性を `@property` 化
**対象ファイル:** `src/backend/engine.py` (66-68行目付近)
**変更前:**
```python
self.ai_api = llm
self.llm_client = llm
self.client = None
```
**変更後:**
```python
@property
def ai_api(self):
    import warnings
    warnings.warn("ai_api is deprecated, use llm instead", DeprecationWarning, stacklevel=2)
    return self.llm

@property
def llm_client(self):
    import warnings
    warnings.warn("llm_client is deprecated, use llm instead", DeprecationWarning, stacklevel=2)
    return self.llm

# client は None のまままたは削除
```

---

### Step 20: `EngineFacade.__getattr__` を明示委譲メソッドに置換（暫定）
**対象ファイル:** `src/backend/engine_facade.py` (54-60行目)
**方針:** 完全分解までは `__getattr__` を残すが、主要メソッド・プロパティは明示的に定義して型チェックを効かせる
```python
# 明示的に定義するもの（engine_facade.py に追加）
@property
def planner(self): return self._engine.planner
@property
def writer(self): return self._engine.writer
@property
def repo(self): return self._engine.repo
# ... 必要な分だけ
```

---

### Step 21: Phase 2 完了確認・テスト実行
```bash
pytest tests/ -q --tb=short -x
mypy src/ --strict
```
**完了条件:** 全テスト緑、mypy エラー0（新規追加分以外）

---

## Phase 3: 二重DIコンテナ統合 (Step 22-35)

### Step 22: 現状の二重コンテナ比較ドキュメント作成
**アクション:** 両コンテナのプロバイダ一覧を Markdown に出力して差分確認
```bash
# config/container.py のプロバイダ
grep -A2 "providers\." config/container.py

# src/core/container/infra.py, app.py のプロバイダ
grep -A2 "providers\." src/core/container/infra.py
grep -A2 "providers\." src/core/container/app.py
```

---

### Step 23: `src/core/container/infra.py` に不足プロバイダ追加
**対象:** `config/container.py` にのみ存在するプロバイダを `InfraContainer` に追加
**確認項目:**
- `audit_logger` (lambda: None)
- その他ルーター等で使われているもの

---

### Step 24: `config/container.py` を後方互換ラッパーに書き換え
**対象ファイル:** `config/container.py`
**全面書き換え:**
```python
"""
config/container.py - 後方互換ラッパー (v3.0+)
新規コードは src.core.container.AppContainer を使用すること。
"""
from dependency_injector import containers, providers
from src.core.container import AppContainer as _AppContainer
from src.core.container.infra import InfraContainer as _InfraContainer

class Container(_AppContainer):
    """AppContainer の別名（後方互換）"""
    pass

# 既存コードが期待するプロバイダ名を維持
Container.wiring_config = containers.WiringConfiguration(packages=["src", "kernels", "prompts"])

# グローバルシングルトン（後方互換）
_container_singleton = None

def get_container() -> Container:
    global _container_singleton
    if _container_singleton is None:
        _container_singleton = Container()
    return _container_singleton
```

---

### Step 25: ルーター群の import を段階的に切替
**対象:** `src/backend/routers/` 配下 14ファイル
**アクション（1ファイルずつ）:**
1. `from config.container import Container` → `from src.core.container import AppContainer as Container`
2. `Container.db()` 等の呼び出しが動くか確認
3. `pytest tests/integration/test_<router>.py` で個別テスト

---

### Step 26: `src/backend/tasks.py` の import 切替
**対象:** `src/backend/tasks.py`
**同じく import 変更 + 動作確認**

---

### Step 27: `src/backend/sse.py`, `task_helpers.py` の import 切替

---

### Step 28: `src/backend/server.py` の import 切替・lifespan 修正
**注意:** `server.py:41` で `Container.db()` を呼んでいる箇所を新コンテナ対応に

---

### Step 29: `config/__init__.py` のエクスポート整理
**対象:** `config/__init__.py`
**アクション:** `Container`, `get_container` の再エクスポートを維持（後方互換）

---

### Step 30: DI コンテナ統合後の全テスト実行
```bash
pytest tests/ -q --tb=short
```

---

### Step 31: `src/core/container/__init__.py` の `make_container` 整理
**確認:** `AppContainer2` → `AppContainer` リネーム済みか確認、不要なエクスポート削除

---

### Step 32: 未使用プロバイダの削除・整理
**アクション:** 両コンテナ統合後に使われなくなったプロバイダを `InfraContainer` / `AppContainer` から削除

---

### Step 33: wiring_config の整理・重複排除
**確認:** `InfraContainer` と `AppContainer` の `wiring_config.packages` が重複していないか

---

### Step 34: Phase 3 完了確認・リグレッションテスト
```bash
pytest tests/unit tests/integration -q
mypy src/ config/ --strict
```

---

### Step 35: ドキュメント更新（README等のDIコンテナ参照箇所）
**アクション:** `README.md` や開発者向けドキュメントで `config.container` 参照箇所を `src.core.container` に更新

---

## Phase 4: UltimateHegemonyEngine 分解 (Step 36-57)

### Step 36: 分解対象メソッドの洗い出し・分類
**対象:** `src/backend/engine.py` の `UltimateHegemonyEngine` クラス
**アクション:** 全メソッドを以下に分類:
- **Planning 系**: `sync_bible`, `resolve_bible_setting` 等
- **Writing 系**: 直接の執筆メソッド（writerに委譲）
- **Tension 系**: `determine_target_tension`, `validate_tension_deviation`
- **その他**: ユーティリティ的なもの

---

### Step 37: `PlotService` クラス新規作成（テンション管理専門）
**新規ファイル:** `src/backend/plot_service.py`
**内容:** `UltimateHegemonyEngine` からテンション関連メソッドを移植
```python
class PlotService:
    def __init__(self, repo, llm=None):
        self.repo = repo
        self.llm = llm
    
    async def determine_target_tension(self, book_id, ep_num, genre, story_type=None):
        # engine.py から移植
    
    async def validate_tension_deviation(self, ep_num, generated_tension, book_id, tolerance=0.2):
        # engine.py から移植
```

---

### Step 38: `PlotService` の DI 登録
**対象:** `src/core/container/app.py`
**追加:**
```python
plot_service = providers.Factory(
    "src.backend.plot_service.PlotService",
    repo=repo,
    llm=llm,
)
```

---

### Step 39: `UltimateHegemonyEngine` からテンションメソッド削除・委譲化
**対象:** `src/backend/engine.py`
**変更:** `__init__` に `plot_service` 追加、メソッド内部を `self.plot_service.xxx()` に委譲

---

### Step 40: `BibleService` 既存実装の確認・インターフェース統一
**対象:** `src/backend/bible_service.py`
**確認:** 既に `WorldBibleGenerator` として存在。`sync_bible` 等を `BibleService` として抽出・統一

---

### Step 41: `BibleService` を DI 登録・Engine から委譲

---

### Step 42: `WritingService` 既存実装の確認・インターフェース統一
**対象:** `src/backend/writing_service.py`
**確認:** 既に分離済み。Engine の `writer` プロパティと統合されているか確認

---

### Step 43: `PlanningService` 既存実装の確認・統合
**対象:** `src/backend/planning_service.py`
**確認:** 既に分離済み。Engine の `planner` / `planning_agent` との関係整理

---

### Step 44: `CritiqueService` 既存実装の確認・統合
**対象:** `src/backend/critique_service.py`
**確認:** 既に分離済み。Engine の `critique` プロパティと統合

---

### Step 45: `NarrativeService` 既存実装の確認・統合
**対象:** `src/backend/engine_narrative.py` (`NarrativeController`)
**確認:** Engine の `narrative` プロパティと統合

---

### Step 46: `MarketingService` 既存実装の確認・統合
**対象:** `src/agents/marketing.py` (`MarketingAgent`)
**確認:** Engine の `marketing` プロパティと統合

---

### Step 47: `StyleRagService` 既存実装の確認・統合
**対象:** `src/backend/engine_style_rag.py` (`StyleRagManager`)
**確認:** Engine の `style_rag` プロパティと統合

---

### Step 48: `UltimateHegemonyEngine.__init__` の引数削減（第1段階）
**目標:** 42個 → 25個程度
**削除対象:** 既にサービス化されたコンポーネントを `__init__` から除外し、サービス経由でアクセス

---

### Step 49: `UltimateHegemonyEngine` 内部でのサービス委譲プロパティ追加
```python
@property
def plot_service(self) -> PlotService:
    return self._plot_service

@property
def bible_service(self) -> BibleService:
    return self._bible_service
# ...
```

---

### Step 50: `UltimateHegemonyEngine.__init__` の引数削減（第2段階）
**目標:** 25個 → 15個程度
**残すべきコア依存:** `api_key`, `repo`, `db`, `pm`, `ctx_mgr`, `llm`, `cooldown`, `formatter`
**サービス群はプロパティで遅延取得または初期化時に生成**

---

### Step 51: `EngineFacade` の `__getattr__` 削除・明示委譲完成
**対象:** `src/backend/engine_facade.py`
**アクション:** Step 20 で主要プロパティは定義済み。残り全てを明示メソッド/プロパティ化

---

### Step 52: `EngineConfig` の責務拡張確認
**対象:** `src/backend/engine_config.py`
**確認:** 複雑な初期化パラメータを吸収できているか。必要なら追加

---

### Step 53: DI コンテナでの Engine 構成簡素化
**対象:** `src/core/container/app.py`
**変更:** `engine` プロバイダの引数リストを大幅削減

---

### Step 54: 既存テストの Engine 依存箇所修正
**アクション:** `grep -r "UltimateHegemonyEngine" tests/ --include="*.py"` で洗い出し、新インターフェースに合わせて修正

---

### Step 55: 統合テスト実行・リグレッション確認
```bash
pytest tests/integration/ tests/e2e/ -q --tb=short
```

---

### Step 56: 引数数最終確認・ドキュメント更新
**確認:** `UltimateHegemonyEngine.__init__` の引数が 10個以下になっていること
**ドキュメント:** `engine_facade.py` の冒頭コメントを実態に合わせて更新

---

### Step 57: Phase 4 完了確認・全テスト実行
```bash
pytest tests/ -q --tb=short
mypy src/ --strict
```
**完了条件:** 全緑、引数10個以下、型エラー0

---

## Phase 5: 三層モデルflatten + kernels分離 + Streamlit分離 (Step 58-72)

### Step 58: Repository 基底クラスの `_to_domain` 共通化
**対象:** `src/backend/database/repositories/` 配下
**アクション:** `SQLAlchemyRepository` (または共通基底) に `_to_domain` 実装を集約、具象クラスの重複実装を削除

---

### Step 59: Pydantic DB Model (`src/models/db.py`) を返却標準に統一
**対象:** 全 Repository の public メソッド
**方針:** 戻り値を `BibleDbModel`, `PlotDbModel` 等（Pydantic DB Model）に統一
**ドメインモデル (`PlotEpisode` 等) は LLM入出力・API境界のみで使用**

---

### Step 60: `DataRepository` のメソッド戻り値型修正
**対象:** `src/backend/database/repository.py`
**変更:** 型ヒントを `List[PlotDbModel]` 等に変更、実装も `_to_domain` 経由で DB Model を返すよう修正

---

### Step 61: `UnitOfWork` のプロパティ戻り値型修正
**対象:** `src/backend/database/uow.py`
**変更:** `bible`, `books`, `plots` 等のプロパティが返すリポジトリのメソッド戻り値を DB Model に統一

---

### Step 62: ドメインモデル使用箇所の洗い出し・移行
**アクション:**
```bash
grep -r "PlotEpisode\|ChapterDbModel\|CharacterDbModel" src/ --include="*.py" | grep -v "models/plot.py"
```
**対応:** LLMプロンプト構築箇所・APIレスポンス箇所のみドメインモデル変換を残し、内部処理は DB Model で完結

---

### Step 63: `kernels/` 使用箇所の全洗い出し
```bash
grep -r "from kernels" src/ --include="*.py"
grep -r "import kernels" src/ --include="*.py"
```

---

### Step 64: `kernels/tension_utils.py` 等の重複機能特定・移行
**主要対象:** `tension_utils.py`, `tension_service.py` 等の `kernels/` 同名モジュールとの重複
**アクション:** `src/backend/tension_utils.py` を正とする。`kernels/` 側の参照を全て置換

---

### Step 65: `kernels/` 残存使用モジュールの個別移行
**対象:** Step 63 で見つかった各モジュール
**方針:** 1ファイルずつ `src/backend/` または `src/services/` 対応モジュールへ移行、import 置換

---

### Step 66: `kernels/` ディレクトリを `archive/kernels/` へ移動
```bash
mkdir -p archive
git mv kernels archive/kernels
```

---

### Step 67: ルート `services/errors.py` 削除済み確認・`src/services/errors.py` へ Streamlit アダプター追加
**対象:** `src/services/errors.py`
**追加:**
```python
class StreamlitErrorHandler:
    """Streamlit UI層専用のエラーハンドラ。コアロジックからは import しないこと。"""
    
    @staticmethod
    def show(error: Exception, context: str = "不明なエラー"):
        import streamlit as st
        import logging
        logging.error(f"Error in {context}: {error}", exc_info=True)
        st.error(f"❌ {context}: {str(error)}")
    
    @staticmethod
    def show_connection_error():
        import streamlit as st
        st.warning(
            "⚠️ **バックエンドサーバーに接続できません。**\n"
            "サーバーが起動しているか確認してください。",
            icon="🚨",
        )
```

---

### Step 68: `config/file_watcher.py` の Streamlit 依存除去
**対象:** `config/file_watcher.py:120`
**変更:** `import streamlit as st` を削除、コールバック関数を引数で受け取る設計に変更
```python
class ConfigFileHandler(FileSystemEventHandler):
    def __init__(self, on_change_callback=None):
        self.on_change_callback = on_change_callback
    
    def on_modified(self, event):
        if self.on_change_callback:
            self.on_change_callback(event)
```

---

### Step 69: `src/core/state/ui_store.py` と `state_manager.py` の Streamlit 依存分離
**方針:** これらは `streamlit_app/stores/` に移動済みか確認。未移動なら移動し、core から削除

---

### Step 70: `src/shared/utils/__init__.py` の Streamlit 依存除去
**対象:** 46行目の `import streamlit as st`
**アクション:** 該当機能を `streamlit_app/utils/` へ移動、core から削除

---

### Step 71: Streamlit 依存除去後のテスト実行
```bash
pytest tests/unit -q
# Streamlitなし環境でも import が通るか確認
python -c "import src.services.errors; import config.file_watcher; print('OK')"
```

---

### Step 72: 最終全体テスト・受入基準確認
```bash
# 1. 全テスト3回連続緑
for i in {1..3}; do pytest tests/ -q --tb=no; done

# 2. 型チェック
mypy src/ config/ --strict

# 3. 引数数確認
python -c "import inspect; from src.backend.engine import UltimateHegemonyEngine; print(len(inspect.signature(UltimateHegemonyEngine.__init__).parameters))"

# 4. DIコンテナ単一化確認
grep -r "from config.container import" src/ --include="*.py"  # 0件であること

# 5. 生成物未コミット確認
git status --porcelain | grep -E "\.db-(shm|wal)|huey\.db|\.coverage"  # 0件

# 6. __getattr__ 残存確認（プロトコル転送目的除く）
grep -r "__getattr__" src/ --include="*.py" | grep -v "Protocol" | grep -v "__getattr__ ="
```

**完了条件:** 上記全てパス

---

## 実装時の重要原則

1. **1ステップ1コミット** - 各ステップ完了ごとに `git add -A && git commit -m "Step XX: 簡潔な説明"`
2. **テスト先行** - 修正前に該当テストを確認、壊したら即修正
3. **型ヒント必須** - 新規コードはフル型ヒント、mypy strict パス
4. **最小差分** - 1ステップで複数ファイルを同時変更しない
5. **後方互換** - 公開APIは破壊的変更せず、DeprecationWarning で移行期間を設ける

---

## リスク緩和策

| リスク | 対策 |
|--------|------|
| Engine分解で既存ワークフローが壊れる | `EngineFacade` 経由で現行インターフェース完全維持、内部のみ置換 |
| DIコンテナ切替でルーターが動かなくなる | 1ファイルずつ切替・テスト、後方互換ラッパーを残す |
| モデルflattenでDBアクセス層が壊れる | Repository基底クラスで変換ロジック集約、具象クラスは薄く保つ |
| kernels移行で動的ロード機能が失われる | 移行前 `grep -r "importlib.*kernels"` で動的ロード箇所を特定・保護 |

---

## 進捗管理用チェックリスト

```
Phase 1: [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ]
Phase 2: [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ]
Phase 3: [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ]
Phase 4: [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ]
Phase 5: [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ]
Total:   72 steps
```

各 `[ ]` を完了時に `[x]` に更新して進捗管理。