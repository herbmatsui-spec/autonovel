# AutoNovel 実装計画書: Phase 2 (P2)
# アーキテクチャの整理と一本化 (36 Steps)

**目的**: 分裂した執筆サービス（`writing_service` 3兄弟）の統合、`src/agent` と `src/agents` の一元化、DB層の危険な接続ハック撤廃、フロントエンド `App.tsx` のGod Component解体を実施し、保守性の高いモジュラー構造を確立する。  
**対象読者**: 小型・低性能LLM（Small LLM / 7Bクラス等）でも迷わず1ステップずつ順次実行できるように、ファイルパス、修正内容、テストケース名、検証コマンドを厳密に定義。

---

## 📋 全体構成（36ステップ）

- **Part 1 (Step 1-8)**: 執筆サービス（`writing_service`）の統合と責務分離
- **Part 2 (Step 9-14)**: `src/agent` と `src/agents` のディレクトリ統合
- **Part 3 (Step 15-22)**: データベース層の正常化とハック（Wrapper）撤廃
- **Part 4 (Step 23-28)**: サービス層の重複・過剰ディレクトリ整理
- **Part 5 (Step 29-34)**: フロントエンド `App.tsx` の解体とReact Router正常化
- **Part 6 (Step 35-36)**: アーキテクチャ検証テストとP2総合回帰確認

---

## Part 1: 執筆サービス（`writing_service`）の統合と責務分離 (Step 1-8)

### Step 1: 3つの `writing_service` の全メソッド・公開IFの抽出
- **目的**: 統合前の全APIシグネチャを一覧化し、互換性を保証するマッピング仕様を作成。
- **対象ファイル**:
  - `src/backend/writing_service.py` (EngineFacade / パイプライン執筆)
  - `src/services/writing_service.py` (BookScore / 自動再生成ループ)
  - `src/services/writing_services.py` (ProjectContext / 状態バリデーション)
- **変更内容**: `docs/adr/001_writing_service_consolidation.md` を作成し、統合後の公開インターフェースを定義。
- **検証コマンド**: 該当ファイルのメソッド一覧確認。

### Step 2: 統合執筆コア `src/domain/writing/coordinator.py` の新規作成
- **目的**: 執筆パイプラインの中核調整役となる `WritingCoordinator` クラスを作成。
- **対象ファイル**: `src/domain/writing/coordinator.py` (新規作成)
- **変更内容**: `generate_episodes_pipeline`, `generate_single_episode` を含むコアパイプライン実行ロジックを集約。
- **検証テスト**: `tests/unit/domain/writing/test_coordinator.py` (新規作成)
- **実行コマンド**: `pytest tests/unit/domain/writing/test_coordinator.py`

### Step 3: 品質評価・再生成ループ `src/domain/writing/quality_loop.py` の新規作成
- **目的**: `src/services/writing_service.py` が担っていた BookScore 評価と再生成ループを分離。
- **対象ファイル**: `src/domain/writing/quality_loop.py` (新規作成)
- **変更内容**: `evaluate_and_regenerate()` メソッドを実装し、スコア閾値判定とフィードバックパッチ生成を集約。
- **検証テスト**: `tests/unit/domain/writing/test_quality_loop.py` (新規作成)
- **実行コマンド**: `pytest tests/unit/domain/writing/test_quality_loop.py`

### Step 4: 状態バリデーション `src/domain/writing/state_guard.py` の新規作成
- **目的**: `src/services/writing_services.py` (複数形) が担っていた事前検証ロジックを分離。
- **対象ファイル**: `src/domain/writing/state_guard.py` (新規作成)
- **変更内容**: `validate_project_context()`, `ensure_chapter_sequence()` を実装。
- **検証テスト**: `tests/unit/domain/writing/test_state_guard.py` (新規作成)
- **実行コマンド**: `pytest tests/unit/domain/writing/test_state_guard.py`

### Step 5: `src/domain/writing/__init__.py` で統合ファサード `WritingService` を定義
- **目的**: `WritingCoordinator`, `QualityLoop`, `StateGuard` を束ねる単一の `WritingService` ファサードを公開。
- **対象ファイル**: `src/domain/writing/__init__.py`
- **変更内容**: 後方互換性を持つ統合 `WritingService` クラスをエクスポート。
- **検証テスト**: `tests/unit/domain/writing/test_writing_service_facade.py` (新規作成)
- **実行コマンド**: `pytest tests/unit/domain/writing/test_writing_service_facade.py`

### Step 6: レガシーファイル3箇所に薄い互換転送ラッパー（シム）を配置
- **目的**: 既存の `import ...writing_service` を一切壊さずに統合サービスへ透過委譲。
- **対象ファイル**:
  - `src/backend/writing_service.py`
  - `src/services/writing_service.py`
  - `src/services/writing_services.py`
- **変更内容**: 各ファイルのクラス定義を `from src.domain.writing import WritingService` からの継承またはエイリアスに変更。
- **検証コマンド**: `python -c "from src.backend.writing_service import WritingService; from src.services.writing_service import WritingService; from src.services.writing_services import WritingServices"`

### Step 7: DIコンテナ（`AppContainer`）のバインディング更新
- **目的**: `AppContainer.writing_service` が新統合クラスをシングルトンまたはファクトリで提供。
- **対象ファイル**: `src/core/container/app.py` または `src/core/container.py`
- **変更内容**: プロバイダ定義を `src.domain.writing.WritingService` に更新。
- **検証テスト**: `tests/unit/core/test_container_writing_service.py`
- **実行コマンド**: `pytest tests/unit/core/test_container_writing_service.py`

### Step 8: 執筆関連の全単体・統合テストのパス確認
- **目的**: 統合後もエディタ自動保存やエピソード生成が以前と全く同じ動作をすることを実証。
- **対象テスト**: `tests/unit/services/test_editor_autosave.py`, `tests/unit/workflows/test_writing_graph_flow.py`
- **実行コマンド**: `pytest tests/unit/services/test_editor_autosave.py tests/unit/workflows/test_writing_graph_flow.py`

---

## Part 2: `src/agent` と `src/agents` のディレクトリ統合 (Step 9-14)

### Step 9: `src/agent/` 内のモジュール調査と移設先マッピング
- **目的**: `src/agent/hooks/`, `src/agent/memory/`, `src/agent/tools/` の依存先確認。
- **対象ファイル**: `src/agent/` 配下の全ファイル
- **変更内容**: 移設マッピングテーブルを作成。
  - `src/agent/hooks/` -> `src/agents/hooks/`
  - `src/agent/memory/` -> `src/agents/memory/`
  - `src/agent/tools/` -> `src/agents/tools/`
- **検証コマンド**: `git status` で差分確認。

### Step 10: `src/agent/tools/` の `src/agents/tools/` への統合
- **目的**: 重複していたツール定義を `src/agents/` 側に一本化。
- **対象ファイル**: `src/agents/tools/`, `src/agents/tool_handler.py`
- **変更内容**: ファイルの移動とインポートパスの解決。
- **検証テスト**: `tests/unit/agents/test_tool_handler.py`
- **実行コマンド**: `pytest tests/unit/agents/test_tool_handler.py`

### Step 11: `src/agent/memory/` の `src/agents/memory/` への統合
- **目的**: メモリ管理モジュールを `src/agents/` 側に一本化。
- **対象ファイル**: `src/agents/memory/`
- **変更内容**: ファイルの移動とインポートパスの解決。
- **検証テスト**: `tests/unit/agents/test_writer_agent_memory.py`
- **実行コマンド**: `pytest tests/unit/agents/test_writer_agent_memory.py`

### Step 12: `src/agent/hooks/` の `src/agents/hooks/` への統合
- **目的**: フック処理モジュールを `src/agents/` 側に一本化。
- **対象ファイル**: `src/agents/hooks/`
- **変更内容**: ファイルの移動とインポートパスの解決。
- **検証テスト**: `tests/unit/agents/test_hooks.py`
- **実行コマンド**: `pytest tests/unit/agents/ -k "hook"`

### Step 13: `src/agent/` を非推奨エイリアスパッケージ化
- **目的**: 旧パス `import src.agent...` を行うコードに対して警告を出しつつ互換性を維持。
- **対象ファイル**: `src/agent/__init__.py`
- **変更内容**:
  ```python
  import warnings
  warnings.warn("src.agent is deprecated; use src.agents instead", DeprecationWarning, stacklevel=2)
  from src.agents import *
  ```
- **検証コマンド**: `python -c "import src.agent"` で警告が出ることを確認。

### Step 14: エージェント関連テストのオールグリーン確認
- **目的**: エージェント統合によるインポート破損が皆無であることを確認。
- **対象テスト**: `tests/unit/agent/`, `tests/unit/agents/`
- **実行コマンド**: `pytest tests/unit/agents/ tests/unit/agent/`

---

## Part 3: データベース層の正常化とハック（Wrapper）撤廃 (Step 15-22)

### Step 15: `DatabaseConnectionWrapper` の使用箇所棚卸し
- **目的**: `raw_conn._connection` に依存している箇所を全検索。
- **対象ファイル**: `src/backend/database/core.py`, `src/backend/database/repository.py`
- **変更内容**: grep 調査を行い、生コネクション使用箇所を特定。
- **検証コマンド**: `grep -rn "get_conn" src/backend/`

### Step 16: `DatabaseManager.get_connection()` の標準化
- **目的**: 私有プロパティに触れるハックを撤廃し、SQLAlchemy 標準の `AsyncConnection` をコンテキストマネージャで返却。
- **対象ファイル**: `src/backend/database/core.py`
- **変更内容**:
  ```python
  @asynccontextmanager
  async def connection(self) -> AsyncIterator[AsyncConnection]:
      async with self.engine.connect() as conn:
          yield conn
  ```
- **検証テスト**: `tests/unit/database/test_connection_standard.py` (新規作成)
- **実行コマンド**: `pytest tests/unit/database/test_connection_standard.py`

### Step 17: 生SQL文字列実行の段階的排除と `sqlalchemy.text` 必須化
- **目的**: `execute(sql)` で `isinstance(sql, str)` を許容して警告を出していた実装を厳格化。
- **対象ファイル**: `src/backend/database/core.py`
- **変更内容**: SQL文字列が渡された場合、内部で安全に `text()` で包み、警告を出さずに統一的に処理。
- **検証テスト**: `tests/unit/database/test_execute_sql.py`
- **実行コマンド**: `pytest tests/unit/database/test_execute_sql.py`

### Step 18: `DatabaseConnectionWrapper` の完全削除
- **目的**: 脆弱なラッパークラス（約40行）を完全に削除。
- **対象ファイル**: `src/backend/database/core.py`
- **変更内容**: `class DatabaseConnectionWrapper` の定義と関連メソッド（`release_read_conn` 等）を削除。
- **検証テスト**: `tests/unit/database/test_core_cleanup.py`
- **実行コマンド**: `pytest tests/unit/database/`

### Step 19: `UnitOfWork` (UoW) の非同期コンテキスト標準化
- **目的**: `async with UnitOfWork() as uow:` におけるロールバックとコミットの責務を確定。
- **対象ファイル**: `src/backend/database/uow.py`
- **変更内容**: 例外発生時の自動 `rollback()`、正常終了時のクリーンアップ、リポジトリキャッシュの自動消去を保証。
- **検証テスト**: `tests/unit/test_uow_repositories.py`
- **実行コマンド**: `pytest tests/unit/test_uow_repositories.py`

### Step 20: SQLite プラグマ（WAL, busy_timeout）設定のカプセル化
- **目的**: コネクション生成イベントリスナーによる安定したWAL/PRAGMA設定。
- **対象ファイル**: `src/backend/database/core.py`
- **変更内容**: `configure_sqlite_engine()` 内で `connect` リスナーを1箇所にまとめ、多重登録を防止。
- **検証テスト**: `tests/unit/database/test_sqlite_pragmas.py` (新規作成)
- **実行コマンド**: `pytest tests/unit/database/test_sqlite_pragmas.py`

### Step 21: DB並行アクセス負荷テストの作成
- **目的**: 並行リクエスト時に `database is locked` が発生しないことを検証。
- **対象ファイル**: `tests/integration/database/test_concurrency_stress.py` (新規作成)
- **テスト内容**: 20個の非同期タスクから同時に `UnitOfWork` 経由で読み書きを実行し、競合エラーなく完了することを検証。
- **実行コマンド**: `pytest tests/integration/database/test_concurrency_stress.py`

### Step 22: DB関連全テストのオールグリーン確認
- **目的**: データベース層の全単体・統合テストがパスすることを確認。
- **対象テスト**: `tests/unit/database/`, `tests/unit/test_uow_repositories.py`, `tests/unit/test_repository_concurrency.py`
- **実行コマンド**: `pytest tests/unit/database/ tests/unit/test_uow_repositories.py tests/unit/test_repository_concurrency.py`

---

## Part 4: サービス層の重複・過剰ディレクトリ整理 (Step 23-28)

### Step 23: マーケティング機能の一元化
- **目的**: `src/services/marketing.py` と `src/services/marketing/` を `src/services/marketing/` パッケージに統合。
- **対象ファイル**: `src/services/marketing/` 配下
- **変更内容**: `marketing.py` のクラス（`MarketingService` 等）をパッケージの `__init__.py` で公開。
- **検証テスト**: `tests/unit/marketing/test_marketing_ctr_router.py`
- **実行コマンド**: `pytest tests/unit/marketing/`

### Step 24: 監査機能（Audit）のインターフェース統合
- **目的**: `audit_service.py`, `audit_adapter.py`, `audit_aggregator.py` を `src/services/audit/` パッケージへ統合。
- **対象ファイル**: `src/services/audit/`
- **変更内容**: 公開ファサード `AuditAggregatorService` を定義。
- **検証テスト**: `tests/unit/services/test_audit.py`
- **実行コマンド**: `pytest tests/unit/ -k "audit"`

### Step 25: RAG機能の統合と整理
- **目的**: `rag_service.py`, `reflective_rag.py`, `hybrid_retriever.py` を `src/services/rag/` パッケージへ体系化。
- **対象ファイル**: `src/services/rag/`
- **変更内容**: 検索パイプラインのエントリポイントを `RAGPipelineService` として明確化。
- **検証テスト**: `tests/unit/test_sqlite_rag_embedding.py`
- **実行コマンド**: `pytest tests/unit/test_sqlite_rag_embedding.py`

### Step 26: 後方互換エクスポートの定義
- **目的**: `src/services/__init__.py` で整理後の主要サービスクラスを一括エクスポート。
- **対象ファイル**: `src/services/__init__.py`
- **変更内容**: `__all__` に正式公開クラスを明記。
- **検証コマンド**: `python -c "from src.services import WritingService, AuditAggregatorService"`

### Step 27: DIコンテナ（`AppContainer`）のサービスバインディング整理
- **目的**: コンテナ内のプロバイダを統合後の新パスへ同期。
- **対象ファイル**: `src/core/container/app.py`
- **変更内容**: 重複したプロバイダ登録を排除。
- **検証テスト**: `tests/unit/core/test_container.py`
- **実行コマンド**: `pytest tests/unit/core/test_container.py`

### Step 28: サービス層リグレッション防止テスト
- **目的**: 整理後のサービス群が期待通り連携動作することを確認。
- **対象テスト**: `tests/unit/services/`
- **実行コマンド**: `pytest tests/unit/services/`

---

## Part 5: フロントエンド `App.tsx` の解体とReact Router正常化 (Step 29-34)

### Step 29: モーダル管理の分離 (`ModalProvider` / `useModal` の作成)
- **目的**: `App.tsx` 内の `showGraph`, `showMedia`, `showConfig`, `showBookshelf` などの `useState` を分離。
- **対象ファイル**: `frontend/src/context/ModalContext.tsx` (新規作成)
- **変更内容**: モーダルの開閉状態とパラメータを Context 内で集中管理。
- **検証テスト**: `frontend/src/__tests__/ModalContext.test.tsx` (新規作成)
- **実行コマンド**: `cd frontend && npm run test ModalContext`

### Step 30: 生 `window.location` / `popstate` リスナーの完全撤廃
- **目的**: [App.tsx (L63-L75)](file:///e:/hhh/frontend/src/App.tsx#L63-L75) の手動ブラウザ履歴監視コードを削除。
- **対象ファイル**: `frontend/src/App.tsx`
- **変更内容**: 当該 `useEffect` ブロックを削除し、React Router のフック（`useNavigate`, `useLocation`）へ移行。
- **検証コマンド**: `grep -rn "popstate" frontend/src/` でヒット0件を確認。

### Step 31: 宣言的ルーティングの導入
- **目的**: URLパスに応じたページコンポーネントのマウントを標準化。
- **対象ファイル**: `frontend/src/routes.tsx` (新規作成)
- **変更内容**:
  ```tsx
  export const routes = [
    { path: "/", element: <EasyModePage /> },
    { path: "/studio/:bookId?", element: <StudioWorkspacePage /> },
    { path: "/wizard", element: <WizardWorkflowPage /> },
  ];
  ```
- **検証テスト**: `frontend/src/__tests__/routes.test.tsx` (新規作成)
- **実行コマンド**: `cd frontend && npm run test routes`

### Step 32: `App.tsx` のスリム化（Shellコンポーネント化）
- **目的**: 380行あった `App.tsx` を、共通レイアウトとルーターのアウトレットのみを持つシンプルなシェル（100行未満）に改修。
- **対象ファイル**: `frontend/src/App.tsx`
- **変更内容**:
  ```tsx
  export function App() {
    return (
      <AppProviders>
        <AppLayout>
          <Outlet />
        </AppLayout>
        <GlobalModals />
      </AppProviders>
    );
  }
  ```
- **検証コマンド**: `Get-Content frontend/src/App.tsx | Measure-Object -Line` で100行以下を確認。

### Step 33: フロントエンド単体テスト（Vitest）の実行・パス
- **目的**: ルーティング・モーダル分離後も既存のUIコンポーネントテストが全て通ることを確認。
- **対象ディレクトリ**: `frontend/`
- **実行コマンド**: `cd frontend && npm run test`

### Step 34: フロントエンド型チェックとビルド検証
- **目的**: TypeScriptのコンパイルエラーおよびViteビルドエラーが0件であることを確認。
- **対象ディレクトリ**: `frontend/`
- **実行コマンド**: `cd frontend && npm run typecheck && npm run build`

---

## Part 6: アーキテクチャ検証テストとP2総合回帰確認 (Step 35-36)

### Step 35: レイヤ間依存ルール検証テストの作成
- **目的**: ドメイン層が上位層（FastAPIルーターやUI）に依存しないクリーンアーキテクチャの依存方向を静的テストで保証。
- **対象ファイル**: `tests/unit/architecture/test_layer_dependencies.py` (新規作成)
- **テスト内容**: `src/domain/` 配下のファイルが `src/backend/routers/` をインポートしていないことを AST 解析で検証。
- **実行コマンド**: `pytest tests/unit/architecture/test_layer_dependencies.py`

### Step 36: P2 全体回帰テストの実行
- **目的**: P1およびP2で改修した全機能が正常に協調動作することを総合確認。
- **対象ディレクトリ**: `tests/` 全体
- **実行コマンド**: `pytest -p no:cacheprovider --tb=short`
- **合格基準**: `failed=0, errors=0` を確認し、P2 を完了とする。
