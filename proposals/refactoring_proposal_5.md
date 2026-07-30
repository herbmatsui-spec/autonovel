# 第5次リファクタリング案

> 作成日: 2026-07-30
> 対象プロジェクト: 覇権エンジン (Novel Writing AI System)
> 事前に実施済み: GlobalConfigModel統合 (step1), テスト基盤整備 (TEST_EXECUTION_INCONSISTENCY_PLAN)

---

## 背景

前回までのリファクタリングで設定モデルの重複排除とテスト基盤の不整合解消が完了している。本提案は、残存するアーキテクチャ上の主要問題——Godクラス、二重DIコンテナ、グローバル状態、デッドコード——に焦点を当てる。

---

## 優先順位 第1位: UltimateHegemonyEngine の神クラス分解

### 現在の問題

[`src/backend/engine.py`](../src/backend/engine.py:21) の `UltimateHegemonyEngine` は **42個のコンストラクタ引数** を持つGodクラスとして振る舞っている。DIコンテナ定義（[`src/core/container.py:149`](../src/core/container.py:149)）では `engine = providers.Factory(...)` に18個の依存を直接注入しており、循環依存やテスタビリティの低下を招いている。

同一ファイルには `determine_target_tension` / `validate_tension_deviation` のような具体メソッドが混在し、関心事の分離が破綻している。

さらに [`src/backend/engine_facade.py`](../src/backend/engine_facade.py:5) 自身が「42引数の神クラス」を認めつつ、`__getattr__` による委譲で問題を先送りにしている。

### リスク

- 新規機能追加時に全機能が1クラスに集中し、競合が常態化
- 単体テストが fixture 構築に18個の依存を必要とし、テスト不可能な領域が増加
- `__getattr__` 委譲により IDE 補完・型チェッカーが無効化

### 提案

1. **`EngineFacade` を正式な Facade に昇格**し、`__getattr__` を削除する
2. `UltimateHegemonyEngine` を以下のドメインサービスに分解:
   - `PlotService` — プロット生成・テンション管理（`engine_plot.py`, `tension_utils.py` を統合）
   - `WritingService` — 本文執筆・推敲（既に `src/backend/writing_service.py` として分離済み、gatewayとして確定）
   - `PlanningService` — 企画・構成 (同様に `planning_service.py` として分離済み)
   - `BibleService` — 世界観設定管理
   - `CritiqueService` — 論理監査・品質評価
   - `NarrativeService` — ナラティブ制御
3. **EngineConfig** の責務を拡張し、複雑な初期化パラメータを単一の値オブジェクトに集約する
4. 残る `UltimateHegemonyEngine` はワイヤリングのためだけの軽量オーケストレータに縮小

### 工数目安: 3〜4日

---

## 優先順位 第2位: 二重DIコンテナの統合

### 現在の問題

プロジェクトに **2つの独立したDIコンテナ** が共存している:

| コンテナ | 定義場所 | 使用箇所 |
|----------|---------|---------|
| `config.container.Container` | [`config/container.py:10`](../config/container.py:10) | `server.py`, 全ルーター (`routers/` 配下 x14)、`tasks.py`, `sse.py`, `task_helpers.py` |
| `src.core.container.InfraContainer` + `AppContainer2` | [`src/core/container/infra.py:18`](../src/core/container/infra.py:18), [`app.py:18`](../src/core/container/app.py:18) | ワークフロー系 (`auto_workflow_pipeline.py`, `writing_service.py` 等) |

両コンテナは以下のプロバイダを重複定義している:
- `db`: `DatabaseManager` (同じクラス、同じ引数)
- `config` / `global_config`: `GlobalConfigModel.load` / `GlobalConfig` (同じモジュール)
- `vector_store`: `ChromaVectorStore`
- `audit_logger`: `lambda: None`
- `cooldown`: `AdaptiveCooldown`
- `llm_factory`, `llm`, `genai_client`, `semantic_cache` 等

`config/container.py` 側には `get_container()` というグローバルSingletonパターンが含まれ、新規コードは `src/core/container/` を推奨されているが、ルーター群は旧コンテナに束縛されている。

### リスク

- プロバイダ修正時に2箇所の編集が必要（既に乖離が発生している可能性）
- テスト時にどちらを使うべきか混乱し、`Container.db()` vs `InfraContainer.db()` の不整合が発生
- wiring_config の指定がコンテナごとに異なる

### 提案

1. **`src/core/container/` を唯一の真実のソース（SSOT）**とする
2. `config/container.py` の `Container` と `get_container()` を **後方互換ラッパー**に縮小:
   ```python
   # config/container.py（最終形）
   from src.core.container import AppContainer as _AppContainer
   
   class Container(_AppContainer):
       wiring_config = _AppContainer.wiring_config
   
   def get_container() -> Container:
       return Container()
   ```
3. ルーター群の import を段階的に `config.container` → `src.core.container` に移行
4. 旧コンテナのみに存在した固有プロバイダ（あれば）を `InfraContainer` に統合

### 工数目安: 1〜2日

---

## 優先順位 第3位: デッドコード・生成物の一掃

### 現在の問題

**デッドモジュール（プロダクションコードから参照されていない）:**

| ファイル | 状況 |
|----------|------|
| [`src/database/uow.py`](../src/database/uow.py) | 実体は [`src/backend/database/uow.py`](../src/backend/database/uow.py) に存在。本ファイルは空/UoW定義が無い（実際には上流域から import されるが、`src/database/` 下には `uow.py` のみで `__init__.py` すらない） |
| ルート [`services/errors.py`](../services/errors.py) | `src/services/errors.py` の再エクスポート stubs。自身で `import streamlit` しておりコアにStreamlit依存を注入している |
| ルート [`services/tracing_service.py`](../services/tracing_service.py) | `TraceLogger` の孤立実装。`src/services/tracing_service.py` と重複 |

**生成物のGit混入:**

```
src/backend/kaku_hegemony_v2 (1).db-shm
src/backend/kaku_hegemony_v2_huey.db
src/backend/kaku_hegemony_v2.db-shm
src/backend/kaku_hegemony_v2.db-wal
database/
alembic.ini
.huey.db（ルート）
```

**孤立テスト（pytest.ini の testpaths=tests により収集されない）:**

```
test_api.py
test_db.py
test_db_lock.py
test_exact_scenario.py
test_manual_sharp_edge.py
test_new_sharp_edge.py
```

**その他:**
- `models/plot.py` — `src/models/__init__.py` は `from src.models.plot import *` を実行するが `src/models/plot.py` は存在しない（`models/plot.py` はルートに存在）。この import は常に失敗するか、少なくとも不安定。

### リスク

- デッドコードが新規開発者の混乱の原因
- `.db-shm/.db-wal` がdiffを汚染し、マージ競合を誘発
- ルート `test_*.py` が腐敗し、バグの発見機会を逃す

### 提案

1. `src/database/uow.py` を **削除**（`src/backend/database/uow.py` が実体）
2. ルート `services/` ディレクトリを **削除**（`src/services/` に完全移行済み）
3. Gitから生成物を削除し、`.gitignore` を拡充:
   ```
   *.db-shm
   *.db-wal
   *.db-journal
   huey.db
   .coverage
   coverage.xml
   ```
4. ルート `test_*.py` 6ファイルを以下に処分:
   - `test_api.py`, `test_db.py`, `test_db_lock.py` → `tests/integration/` へ移設
   - `test_exact_scenario.py`, `test_manual_sharp_edge.py`, `test_new_sharp_edge.py` → `tests/e2e/` へ移設
5. `src/models/__init__.py` の `from src.models.plot import *` を修正（`models/plot.py` の内容を `src/models/plot.py` に移動、または import パスを修正）

### 工数目安: 0.5〜1日

---

## 優先順位 第4位: グローバル singleton 状態の contextvars 化

### 現在の問題

5箇所でグローバルSingleton/クラス変数が使用され、テストの分離性を破壊している:

|  Singleton  | 定義場所 | 影響範囲 |
|-------------|---------|---------|
| `_GLOBAL_DB_MANAGER` | [`src/backend/database/core.py:288`](../src/backend/database/core.py:288) | `get_db_manager()`, `set_db_manager()` — テスト間で状態がリーク |
| `TraceContext._current_trace_id` | [`src/core/observability.py:12`](../src/core/observability.py:12) | クラス変数。非同期タスク間でトレースIDが共有され、`test_trace_context_isolation` が失敗 |
| `PluginLoader._instance` | [`src/core/plugin_loader.py:9`](../src/core/plugin_loader.py:9) | ロード順序に依存したシングルトン |
| `ConfigManager._instance` | [`config/settings.py`](../config/settings.py) | 旧実装の名残（step1で移行推奨済みだが残存） |
| `EngineService._instance` | [`src/engine_service.py`](../src/engine_service.py) | 起動順序依存 |

### リスク

- テストの実行順序が結果に影響する（flakyテストの主因）
- 非同期コンテキストでグローバル変数が上書きされ、トレース追跡が破損
- 並列テストが不可能

### 提案

1. **`TraceContext._current_trace_id`** → `contextvars.ContextVar` に移行:
   ```python
   _current_trace_id: ContextVar[Optional[str]] = ContextVar("_current_trace_id", default=None)
   ```
   非同期タスク間で自動的に分離されることを保証。

2. **`_GLOBAL_DB_MANAGER`** → DIコンテナ経由に移行:
   - テスト時は `InfraContainer.db()` からテスト用DBを注入
   - `set_db_manager()` は残存させるが、内部で `_GLOBAL_DB_MANAGER` への直接代入をやめ、DI delegate に委譲

3. **`PluginLoader`** → スタティックメソッド化またはDIサービス化:
   - シングルトンロジックを削除し、`PluginLoader.load_all()` を起動時に1回呼ぶだけの設計に

4. `ConfigManager._instance` と `EngineService._instance` を同様にDI委譲またはcontextvars化

### 工数目安: 1日

---

## 優先順位 第5位: 動的 `__getattr__` の一掃

### 現在の問題

5箇所で `__getattr__` がAPIを動的に委譲/変換している:

| クラス | ファイル | `__getattr__` の用途 |
|--------|---------|---------------------|
| `EngineFacade` | [`engine_facade.py:54`](../src/backend/engine_facade.py:54) | 内包 `UltimateHegemonyEngine` の属性へ委譲 |
| `PlotEpisode` | [`models/plot.py:409`](../models/plot.py:409) | `self_critique` の別名解決、`analytics`/`foreshadowing`/`extra_engines` へのフォールバック |
| `DatabaseConnectionWrapper` | [`src/backend/database/core.py:94`](../src/backend/database/core.py:94) | `dbapi_conn` への属性委譲 |
| `UltimateHegemonyEngine`（イニシャリザ） | [`engine.py:66`](../src/backend/engine.py:66) | `ai_api`/`llm_client`/`client` のエイリアス設定 |

### リスク

- IDE補完・型チェッカーが無効化され、リファクタリング時に参照追跡が不可能
- `AttributeError` が実行時まで検出されない
- `PlotEpisode.__getattr__` は `tension` や `catharsis` 等の属性を `analytics` に委譲するが、Pydanticモデルのバリデーションをバイパスする可能性

### 提案

1. **`EngineFacade.__getattr__`** → 必要性がなくなるまで（Godクラス分解完了後）明示的プロパティ/メソッドに置換
2. **`PlotEpisode.__getattr__`** → `@property` で明示的に公開:
   ```python
   @property
   def tension(self) -> int:
       return self.analytics.tension
   ```
   `self_critique` は既に `@field_validator` で別名解決可能なため、`__getattr__` 自体を削除
3. **`DatabaseConnectionWrapper.__getattr__`** → `dbapi_conn` への直接アクセスを明示的にラップメソッド化、または型安全なプロキシに置換
4. **`UltimateHegemonyEngine` のエイリアス** (`ai_api`, `llm_client`) → 削除または `@property` 化。前方互換性が必要な場合は非推奨警告付きで移行期間を設ける

### 工数目安: 1日

---

## 優先順位 第6位: 三層モデル階層の flatten 検討

### 現在の問題

同じドメインエンティティが3層で表現されている:

```
SQLAlchemy ORM (src/backend/database/models.py)
    ↓ select() / INSERT
Pydantic DB Models (src/models/db.py — BibleDbModel, PlotDbModel, etc.)
    ↓ リポジトリが _to_domain() で変換
Pydantic Domain Models (models/plot.py — PlotEpisode, ChapterDbModel 等)
```

`DataRepository` は全メソッドで明示的な `_to_domain()` 変換を行い、`UnitOfWork` のプロパティも同様に2種類のモデルを返却する。

### リスク

- フィールド追加時に3層全ての更新が必要
- `_to_domain()` の実装漏れや不整合が頻発
- パフォーマンスオーバーヘッド（大量のエピソード変換時）

### 提案

1. **Repository の戻り値を Pydantic DB Model に統一**し、ドメインモデルは LLM入出力やAPI境界のみに使用する
2. または、**SQLAlchemy ORM と Pydantic DB Model を unified model** にする（SQLAlchemy 2.0 の `Mapped` + Pydantic統合）
3. 変換ロジックを一箇所（Repository基底クラス）に集約し、具象リポジトリでの重複変換を排除

### 工数目安: 2〜3日

---

## 優先順位 第7位: kernels/ 層と engine 層の責務分離

### 現在の問題

`kernels/` ディレクトリに **22ファイル** のモジュールが存在し、古いアーキテクチャ層として機能している:

```
kernels/
  base.py, body_language.py, comfort.py, conflict.py,
  connection_kernel.py, connection.py, dialogue.py,
  engines.py, enigma.py, graph.py, hegemony.py,
  interaction_config.py, interaction_formatter.py,
  interaction_manager.py, interaction_trigger.py, memory.py,
  pipeline.py, pov.py, preset_triggers.py, resonance.py,
  serenity.py
```

一方、`src/backend/engine_*.py` に同じ責務を持つモジュールが散在:
- `engine_plot.py`, `engine_narrative.py`, `engine_critique.py`, `engine_style_rag.py`, `engine_utils.py`, `tension_utils.py`, `tension_service.py`

どちらが「正」の実装か不明確で、`from kernels.xxx import ...` と `from src.backend.engine_xxx import ...` が混在している。

### リスク

- 修正時にどちらを触るべきか判断コストが発生
- 重複実装の不整合（例: `tension` 計算が `kernels/` と `src/backend/tension_utils.py` の両方に存在）
- 新規開発者が学習時に混乱

### 提案

1. `kernels/` を **レガシー層**と位置付け、`src/backend/engine_*.py` / `src/backend/services/` を正規実装とする
2. 各 `kernels/*.py` の使用箇所をgrepで洗い出し、正規実装へ移行
3. 移行完了後、`kernels/` を `archive/kernels/` へ退避（削除はしない）
4. または、`kernels/` を`plugins`システムの一部として再定義し、動的ロード可能にする

### 工数目安: 2〜3日

---

## 優先順位 第8位: Streamlit 依存の core/src からの分離

### 現在の問題

[`services/errors.py`](../services/errors.py:9)（ルート）が `import streamlit as st` し、`st.error()` / `st.warning()` でUI表示を行っている。これは `src/services/errors.py` (`retry_on_lock`) から再エクスポートされているため、コアロジックをインポートした瞬間にStreamlitランタイムが必要になる。

加えて:
- [`src/core/state/ui_store.py:7`](../src/core/state/ui_store.py:7)
- [`src/core/state/state_manager.py:11`](../src/core/state/state_manager.py:11)
- [`config/file_watcher.py:120`](../config/file_watcher.py:120)
- [`src/shared/utils/__init__.py:46`](../src/shared/utils/__init__.py:46)

がStreamlitを直接importしている。

### リスク

- CLI/バッチ処理から`src.services.errors`をimportできない
- ユニットテストがStreamlitランタイムを要求する
- `config/file_watcher.py` はホットリロード基盤であり、Streamlit依存によりサーバー単体起動時に使用不可

### 提案

1. `services/errors.py`（ルート）を**削除**（既に `src/services/errors.py` が実体）
2. `src/services/errors.py` に `StreamlitErrorHandler` アダプターを追加:
   ```python
   # src/services/errors.py
   class StreamlitErrorHandler:
       @staticmethod
       def show(error: Exception, context: str):
           import streamlit as st
           st.error(f"❌ {context}: {error}")
   ```
   コアロジックからStreamlit importを削除し、UI層でのみ使用
3. `config/file_watcher.py` のStreamlit importをコールバック注入に置換（`TEST_EXECUTION_INCONSISTENCY_PLAN.md` の優先順位第8位と同様の改良）
4. `src/core/state/` のStreamlit依存を `streamlit_app/stores/` へ移動

### 工数目安: 1日

---

## サマリ

| # | 提案 | 影響範囲 | 難易度 | 期待効果 |
|---|------|---------|--------|---------|
| 1 | UltimateHegemonyEngine分解 | 高（全エンジンコール） | 高 | ★★★★★ |
| 2 | 二重DIコンテナ統合 | 中（ルーター群） | 中 | ★★★★ |
| 3 | デッドコード一掃 | 低（削除のみ） | 低 | ★★★ |
| 4 | グローバルSingleton解消 | 高（テスト安定性） | 中 | ★★★★ |
| 5 | __getattr__一掃 | 中（型安全性） | 低 | ★★★ |
| 6 | 三層モデルflatten | 高（Repository全域） | 高 | ★★★★ |
| 7 | kernels/責務分離 | 中（22ファイル） | 中 | ★★★ |
| 8 | Streamlit分離 | 中（core/src） | 低 | ★★★ |

---

## 推奨実施順序

```
Phase 1（即時）: #3 デッドコード一掃（リスク最小・即効果）
Phase 2（1週目）: #4 グローバルSingleton解消 → #5 __getattr__一掃（テスト安定化）
Phase 3（2週目）: #2 二重DIコンテナ統合（基盤整備）
Phase 4（3〜4週目）: #1 UltimateHegemonyEngine分解（最大効果・高難易度）
Phase 5（並行）: #6 三層モデルflatten → #7 kernels/分離 → #8 Streamlit分離
```

## 受入基準

- `pytest tests/` が **3回連続**で全件green（順序入れ替え含む）
- `mypy src/ --strict` がエラー0件
- `UltimateHegemonyEngine.__init__` の引数が **10個以下**に削減
- DIコンテナ定義が **1箇所のみ**（`src/core/container/`）に集約
- `git ls-files '*.db-shm' '*.db-wal' 'huey.db'` が0件
- `__getattr__` が **0箇所**（protocol転送目的のものを除く）
