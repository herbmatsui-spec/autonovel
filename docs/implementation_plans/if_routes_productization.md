# IF ルート分岐 製品化 詳細実装計画書（72 ステップ）

**作成日:** 2026-09-03
**ステータス:** 📋 レビュー待ち
**対象:** `src/easy_mode/phase3/if_routes.py`（1205 行、完成済み）を製品の中核機能へ昇格
**関連計画:** `IMPLEMENTATION_PLAN.md` §3「IF ルート分岐（ストーリー分岐/フォーク）- 約30% 完了」

## 0. メタ方針（設計決定事項）

| # | 項目 | 決定 | 反映先ステップ |
|---|------|------|---------------|
| Q1 | `multimedia.py:125 generate_if_routes` | **残す（移行しない）** | 新 `/api/branches` と並存、削除しない |
| Q2 | DB マイグレーション方式 | **Alembic** | 全マイグレーションは `alembic revision` で発行 |
| Q3 | WebSocket 採用 | **FastAPI 標準 WS** | `@router.websocket()` を採用、Socket.IO は不採用 |
| Q4 | EPUB3 スコープ | **基本スジのみ** | 複数 EPUB に分割出力。`epub:type="choice"` は扱わない |
| Q5 | `branch_id=1` 互換 | **デフォルトとして残す** | `branch_id: int = 1` を全箇所で温存、新規列追加なし |

## 1. 現状分析サマリ

### 1.1 既存資産

- **完成済みコア**: `src/easy_mode/phase3/if_routes.py` 1205 行
  - 公開クラス: `BranchType`, `ConditionOperator`, `BranchCondition`, `RouteNode`, `IFRouteGraph`, `IFRouteGenerator`, `IFRoutePlayer`
  - 公開 API: `IFRouteGenerator.generate_from_series`, `IFRoutePlayer.make_choice`, `load_save`, `get_state`, `export_playthrough`
- **DB モデル**: `src/domain/models/branch.py::BranchDbModel`（id, book_id, name, parent_id, fork_ep_num, created_at）
- **プロット接続**: `src/domain/models/plot.py::branch_id: int = 1`, `src/domain/models/chapter.py::branch_id: int = 1`
- **呼び出し元**: `src/backend/multimedia_service.py::generate_asset_pack()` のみ

### 1.2 `branch_id=1` 固定箇所（影響度マトリクス）

| ファイル:行 | 関数 | 影響度 | ステップ |
|------------|------|--------|---------|
| `src/backend/engine_context.py:116,198,245` | `get_chapters_before(branch_id, ep_num)` | 高 | S37-S39 |
| `src/backend/routers/hooks.py:86-87` | `update_chapter_content(branch_id=1)` | 中 | S40 |
| `src/backend/routers/cost.py:27,53,70` | `aggregate(book_id, branch_id)` | 中 | S41 |
| `src/backend/routers/misc.py:12,64` | `get_trend_metrics(book, branch)` | 中 | S42 |
| `src/backend/writing_service.py:46,74` | `branch_id=1` デフォルト | 中 | S43 |
| `src/backend/tasks/generation_tasks.py:58` | `payload.get("branch_id", 1)` | 中 | S44 |
| `src/backend/tasks/__init__.py:184` | `async_score_narrative_metrics` | 低 | S45 |
| `src/backend/orchestrated.py:25` | `branch_id: int = Field(default=1)` | 低 | S46 |

### 1.3 テスト & Lint 基盤

- `pytest --cov-fail-under=80` (`pyproject.toml`)
- `pytest tests/test_migrations.py` で Alembic 検証
- `ruff check src/` / `mypy src/` (`pyproject.toml [tool.ruff]` / `[tool.mypy]`)

## 2. エピソード構成（6 × 12 = 72 ステップ）

| Ep | ステップ | ゴール | 主要な変更 |
|----|----------|--------|-----------|
| 1 | S01-S12 | スキーマ・マイグレーション・Branch モデル拡張 | 新マイグレーション ×2、新 repo |
| 2 | S13-S24 | Branch CRUD + IF Graph シリアライズ | `routers/branches.py`、`schemas/branch.py` |
| 3 | S25-S36 | Player セッション REST API + 永続化 | `branch_play_sessions` テーブル、FastAPI REST |
| 4 | S37-S48 | `branch_id=1` 固定コード脱却 | §1.2 マトリクス準拠、互換維持 |
| 5 | S49-S60 | FastAPI 標準 WS + エディタ UI ベース | `@router.websocket()`、HTML 最小 UI |
| 6 | S61-S72 | EPUB 基本スジ + 統計 + E2E | 分割出力、`/branches/{id}/stats`、E2E |

## 3. ステップ一覧と依存 DAG

```
S01-S06 ──┐
          ├─ S07-S12 ──┐
S13-S15 ──┤            ├─ S25-S30 ──┐
S16-S18 ──┤            │             ├─ S49-S54 ──┐
S19-S24 ──┴─ S31-S36 ─┴─ S37-S48 ───┘             ├─ S61-S66 ──┐
                                                       S67-S72
```

凡例：前行完了が次行着手条件。1 エピソード内で 1 ステップずつ。

---

## Episode 1: スキーマ・マイグレーション・Branch モデル拡張 (S01-S12)

### S01 Alembic 環境確認

- **目的**: Alembic 設定が既存マイグレーションで正常動作することを確認
- **前提**: なし
- **変更ファイル**: なし（確認のみ）
- **検証**:
  ```bash
  pytest tests/test_migrations.py::test_alembic_config_loads -v
  ```
- **ロールバック**: 不要
- **Low-LLM メモ**: `alembic.ini` の `script_location` が `src/backend/alembic` か確認

### S02 新マイグレーション「0015_add_branches_core」雛形作成

- **目的**: `branches` テーブルと IF Graph 用 JSON 列を Alembic で追加
- **前提**: S01
- **変更ファイル**: `src/backend/alembic/versions/0015_add_branches_core.py`（新規）
- **追加内容**: `op.create_table("branches", ...)` + `plot_id` FK
  ```python
  def upgrade() -> None:
      op.create_table(
          "branches",
          sa.Column("id", sa.Integer, primary_key=True),
          sa.Column("book_id", sa.Integer, sa.ForeignKey("books.id"), nullable=False),
          sa.Column("name", sa.String(255), nullable=False),
          sa.Column("parent_id", sa.Integer, sa.ForeignKey("branches.id"), nullable=True),
          sa.Column("fork_ep_num", sa.Integer, nullable=True),
          sa.Column("graph_json", sa.JSON, nullable=True),
          sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
      )
  ```
- **検証**: `alembic upgrade head` 後 `sqlite3 autonovel.db ".schema branches"`
- **ロールバック**: `alembic downgrade -1`
- **Low-LLM メモ**: 既存 `0014_add_patch_review_and_setting_version.py` の構造を完全コピーし、テーブル名と列だけ変更

### S03 マイグレーション「0015」のダウングレード確認

- **目的**: upgrade/downgrade 往復で完全に戻せることを担保
- **前提**: S02
- **検証**:
  ```bash
  alembic downgrade base && alembic upgrade head
  pytest tests/test_migrations.py::test_migration_roundtrip -v
  ```
- **ロールバック**: なし

### S04 `BranchDbModel` 拡張（Pydantic 側）

- **目的**: 既存 `BranchDbModel` に `graph_json: dict | None` を追加
- **変更ファイル**: `src/domain/models/branch.py`
- **追加内容**:
  ```python
  class BranchDbModel(BaseModel):
      id: int
      book_id: int
      name: str
      parent_id: int | None = None
      fork_ep_num: int | None = 0
      graph_json: dict[str, Any] | None = None
      created_at: datetime | None = None
  ```
- **検証**: `python -c "from src.domain.models.branch import BranchDbModel; print(BranchDbModel.model_fields)"`
- **ロールバック**: `git revert` S04

### S05 `BranchDbModelCreate` / `BranchDbModelUpdate` 追加

- **目的**: CRUD 用 Pydantic モデル
- **変更ファイル**: `src/domain/models/branch.py`
- **追加内容**: `BranchDbModelCreate`（id, parent_id, fork_ep_num, name のみ）, `BranchDbModelUpdate`（name, fork_ep_num）
- **検証**: `python -c "from src.domain.models.branch import BranchDbModelCreate; b = BranchDbModelCreate(book_id=1, name='main')"`
- **ロールバック**: `git revert` S05

### S06 SQLAlchemy ORM モデル `BranchORM` 追加

- **目的**: `branches` テーブルに対応する ORM クラス
- **変更ファイル**: `src/backend/database/models/branch.py`（新規）
- **追加内容**:
  ```python
  class BranchORM(Base):
      __tablename__ = "branches"
      id = Column(Integer, primary_key=True)
      book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
      name = Column(String(255), nullable=False)
      parent_id = Column(Integer, ForeignKey("branches.id"), nullable=True)
      fork_ep_num = Column(Integer, nullable=True)
      graph_json = Column(JSON, nullable=True)
      created_at = Column(DateTime, server_default=func.now())
  ```
- **検証**: `python -c "from src.backend.database.models.branch import BranchORM; print(BranchORM.__tablename__)"`
- **ロールバック**: S05 同様

### S07 Alembic 環境への `BranchORM` 登録

- **目的**: `alembic env.py` で `BranchORM` を自動検出
- **変更ファイル**: `src/backend/alembic/env.py`
- **追加内容**: `from src.backend.database.models.branch import BranchORM` を `target_metadata` 側に追記
- **検証**: `alembic check` がエラーなく完了
- **ロールバック**: 該当行を `git revert`

### S08 マイグレーション「0016_add_branch_play_sessions」作成

- **目的**: `IFRoutePlayer` のセッション状態保存用テーブル
- **変更ファイル**: `src/backend/alembic/versions/0016_add_branch_play_sessions.py`（新規）
- **追加内容**: `branch_play_sessions` テーブル
  ```python
  op.create_table(
      "branch_play_sessions",
      sa.Column("id", sa.String(36), primary_key=True),
      sa.Column("book_id", sa.Integer, nullable=False),
      sa.Column("branch_id", sa.Integer, nullable=False),
      sa.Column("current_node_id", sa.String(255)),
      sa.Column("context_json", sa.JSON),
      sa.Column("save_points_json", sa.JSON),
      sa.Column("status", sa.String(20), server_default="active"),
      sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
  )
  ```
- **検証**: `alembic upgrade head` でテーブル存在確認
- **ロールバック**: `alembic downgrade -1`

### S09 `BranchPlaySessionORM` 追加

- **目的**: `branch_play_sessions` の ORM クラス
- **変更ファイル**: `src/backend/database/models/branch.py`
- **追加内容**: S06 と同ファイルに `BranchPlaySessionORM` を併記
- **検証**: import テスト
- **ロールバック**: `git revert`

### S10 `BranchRepo` 雛形作成

- **目的**: SQLAlchemy ベースの repo クラス
- **変更ファイル**: `src/backend/repos/branch_repo.py`（新規）
- **追加内容**: `class BranchRepo: __init__(self, session: AsyncSession) -> None` のみ（メソッド空）
- **検証**: `pytest tests/branches/test_branch_repo_init.py -v`（雛形のみ）
- **ロールバック**: ファイル削除

### S11 `BranchRepo.create()` / `get()` 実装

- **目的**: 単一 CRUD
- **追加内容**:
  ```python
  async def create(self, data: BranchDbModelCreate) -> BranchDbModel: ...
  async def get(self, branch_id: int) -> BranchDbModel | None: ...
  async def list_by_book(self, book_id: int) -> list[BranchDbModel]: ...
  ```
- **検証**: `pytest tests/branches/test_branch_repo_crud.py::test_create_and_get -v`
- **ロールバック**: ファイル削除

### S12 `BranchRepo` ツリー取得メソッド

- **目的**: `parent_id` を使ったツリー構造返却
- **追加内容**: `async def get_tree(self, book_id: int) -> list[BranchDbModel]: ...`
- **検証**: 既存テスト無劣化 + 新テスト追加
- **ロールバック**: メソッドのみ削除

**Episode 1 完了条件**:
- [ ] `alembic upgrade head` がエラーなく完走
- [ ] `tests/branches/test_branch_repo_*.py` が全通過
- [ ] 既存 `tests/test_migrations.py` 無劣化

---

## Episode 2: Branch CRUD + IF Graph シリアライズ (S13-S24)

### S13 FastAPI スキーマ `BranchSchema` 追加

- **目的**: REST リクエスト/レスポンス用 Pydantic
- **変更ファイル**: `src/backend/schemas/branch.py`（新規）
- **追加内容**:
  ```python
  class BranchResponse(BaseModel):
      id: int
      book_id: int
      name: str
      parent_id: int | None
      fork_ep_num: int | None
      created_at: datetime | None
  ```
- **検証**: import テスト
- **ロールバック**: ファイル削除

### S14 `RouteNode.to_dict()` の現状確認

- **目的**: 既存 `if_routes.py:RouteNode.to_dict()` の戻り値 JSON 形式を記録
- **変更ファイル**: なし（読み取りのみ）
- **検証**: `python -c "from src.easy_mode.phase3.if_routes import RouteNode; import json; print(json.dumps(RouteNode(...).to_dict(), indent=2))"`
- **ロールバック**: 不要

### S15 `IFRouteGraph.to_dict()` ヘルパー追加

- **目的**: グラフ全体を JSON シリアライズ
- **変更ファイル**: `src/easy_mode/phase3/if_routes.py`
- **追加内容**:
  ```python
  def to_dict(self) -> dict[str, Any]:
      return {"entry_node_id": self.entry_node_id, "nodes": {nid: n.to_dict() for nid, n in self.nodes.items()}, "metadata": self.metadata}
  ```
- **検証**: 既存 `if_routes` テストが壊れないこと（`pytest tests/test_easy_mode_api.py -v`）
- **ロールバック**: `git revert`

### S16 `IFRouteGraph.from_dict()` ヘルパー追加

- **目的**: JSON → グラフ復元
- **追加内容**:
  ```python
  @classmethod
  def from_dict(cls, data: dict[str, Any]) -> "IFRouteGraph": ...
  ```
- **検証**: `to_dict → from_dict` ラウンドトリップテスト追加
- **ロールバック**: メソッド削除

### S17 `BranchRepo.save_graph()` / `load_graph()` 実装

- **目的**: グラフ JSON の永続化
- **追加内容**:
  ```python
  async def save_graph(self, branch_id: int, graph: IFRouteGraph) -> None: ...
  async def load_graph(self, branch_id: int) -> IFRouteGraph | None: ...
  ```
- **検証**: S15/S16 のラウンドトリップを DB 経由で実施するテスト
- **ロールバック**: メソッド削除

### S18 `routers/branches.py` 雛形作成

- **目的**: FastAPI router の器
- **変更ファイル**: `src/backend/routers/branches.py`（新規）
- **追加内容**: `router = APIRouter(prefix="/api/branches", tags=["branches"])`
- **検証**: import のみ
- **ロールバック**: ファイル削除

### S19 `POST /api/branches/` 実装（create）

- **目的**: 新規ブランチ作成
- **追加内容**:
  ```python
  @router.post("/", response_model=BranchResponse)
  async def create_branch(payload: BranchDbModelCreate, repo: BranchRepo = Depends(get_branch_repo)) -> BranchResponse: ...
  ```
- **検証**: `pytest tests/branches/test_branch_api.py::test_create -v` + curl smoke
- **ロールバック**: メソッド削除

### S20 `GET /api/branches/{book_id}` 実装（list + tree）

- **目的**: 書籍配下の全ブランチをツリーで返却
- **追加内容**: `@router.get("/{book_id}", response_model=list[BranchResponse])`
- **検証**: tree 構造テスト
- **ロールバック**: メソッド削除

### S21 `GET /api/branches/{book_id}/graph` 実装

- **目的**: 指定書籍の最新グラフ取得
- **追加内容**: `load_graph()` を呼び `IFRouteGraph.to_dict()` を返却
- **検証**: グラフ JSON 検証
- **ロールバック**: メソッド削除

### S22 `POST /api/branches/{book_id}/fork` 実装

- **目的**: 既存ブランチから分岐作成
- **追加内容**: `fork_ep_num` 時点の `plots.branch_id` を参照し、新規 Branch 作成
- **検証**: fork 前後で parent_id が正しく張られること
- **ロールバック**: メソッド削除

### S23 `POST /api/branches/{book_id}/merge` 実装

- **目的**: 2 ブランチを合流
- **追加内容**: `merge_ep_num` で MERGE ノード作成し `RouteNode.branch_type = BranchType.MERGE` を挿入
- **検証**: マージ後のグラフに MERGE ノードが含まれる
- **ロールバック**: メソッド削除

### S24 router 登録

- **目的**: メインアプリへ `branches` router を登録
- **変更ファイル**: `src/backend/main.py`（または `routers/__init__.py`）
- **追加内容**: `app.include_router(branches.router)`
- **検証**: `pytest tests/test_health.py -v` + OpenAPI に `/api/branches` が現れること
- **ロールバック**: 1 行削除

**Episode 2 完了条件**:
- [ ] `GET /api/branches/{book_id}` がツリー返却
- [ ] OpenAPI に新エンドポイントが表示
- [ ] 既存テスト無劣化

---

## Episode 3: Player セッション REST API + 永続化 (S25-S36)

### S25 `BranchPlaySessionRepo` 雛形

- **変更ファイル**: `src/backend/repos/branch_play_session_repo.py`（新規）
- **追加内容**: `class BranchPlaySessionRepo: __init__(self, session: AsyncSession)`
- **検証**: import テスト

### S26 セッション CRUD `create()` / `get()` / `list_by_book()`

- **追加内容**: `BranchPlaySessionORM` への基本操作
- **検証**: 単体テスト

### S27 セッション状態保存 `update_state()` 実装

- **追加内容**:
  ```python
  async def update_state(self, session_id: str, current_node_id: str, context: dict, save_points: list) -> None: ...
  ```
- **検証**: JSON シリアライズ往復テスト

### S28 `POST /api/branches/play` 実装（セッション開始）

- **追加内容**: `book_id` + `branch_id` を受け `uuid4` の session_id を発行
- **検証**: `pytest tests/branches/test_player_api.py::test_start_session -v`

### S29 `GET /api/branches/play/{session_id}/state` 実装

- **追加内容**: `IFRoutePlayer.get_state()` を DB から復元して返却
- **検証**: 状態整合性テスト

### S30 `POST /api/branches/play/{session_id}/choose` 実装

- **追加内容**: `choice_id` を受け `IFRoutePlayer.make_choice()` を呼出、結果を DB に保存
- **検証**: 選択肢テスト

### S31 `POST /api/branches/play/{session_id}/save` 実装

- **追加内容**: 現状態を `save_points` に追記保存
- **検証**: save 後のロードで状態一致

### S32 `POST /api/branches/play/{session_id}/load` 実装

- **追加内容**: 指定 index のセーブポイントから状態復元
- **検証**: ロード後の選択肢提示テスト

### S33 `POST /api/branches/play/{session_id}/end` 実装

- **追加内容**: セッションを `status="completed"` に更新
- **検証**: 一覧から completed が除外される

### S34 `GET /api/branches/play/{session_id}/playthrough` 実装

- **追加内容**: `IFRoutePlayer.export_playthrough()` を返却
- **検証**: 履歴の整合性テスト

### S35 セッション ID のバリデーション

- **追加内容**: UUID 形式チェック
- **検証**: 400 エラーテスト

### S36 同時実行制御（楽観ロック）

- **追加内容**: `updated_at` 一致を条件にした UPDATE
- **検証**: 競合テスト（同一 session_id で 2 並行リクエスト）

**Episode 3 完了条件**:
- [ ] セッション開始 → 選択 → セーブ → ロード が完走
- [ ] 同時実行テスト通過

---

## Episode 4: `branch_id=1` 固定コード脱却 (S37-S48)

> **方針**: `branch_id=1` を **デフォルトとして残す**（Q5）。各ステップは「明示的に渡された `branch_id` を使う」ロジックを導入し、デフォルトを温存する。

### S37 `engine_context.py::get_chapters_before` の `branch_id` 経路追加

- **変更ファイル**: `src/backend/engine_context.py`
- **追加内容**: `engine.book.current_branch_id` を優先、未設定なら `1`
- **検証**: 既存テスト + 新規「`current_branch_id=2` で動作」テスト

### S38 同上: `get_relevant_past_logs`

- **変更**: パラメータ追加
- **検証**: 既存テスト無劣化

### S39 同上: 第 3 箇所（245 行）

- **変更**: 同パターン適用
- **検証**: `pytest tests/test_engine_context.py -v`

### S40 `routers/hooks.py::update_chapter_content`

- **変更**: `branch_id=1` を引数化して、`payload.branch_id` を受け取れるようにする（デフォルト 1 維持）
- **検証**: 既存テスト + 新規分岐テスト

### S41 `routers/cost.py` 3 関数

- **変更**: `branch_id` を query param 化
- **検証**: `pytest tests/test_cost_router.py -v`

### S42 `routers/misc.py::get_narrative_metrics_trend`

- **変更**: path param の `branch_id` を尊重
- **検証**: 既存テスト

### S43 `writing_service.py` 2 関数

- **変更**: `branch_id` 引数を payload から取得
- **検証**: 既存テスト

### S44 `generation_tasks.py::branch_id = payload.get(...)`

- **変更**: デフォルト 1 維持のまま、payload 参照確認
- **検証**: 既存テスト

### S45 `tasks/__init__.py::async_score_narrative_metrics`

- **変更**: `branch_id` をキーワード引数化
- **検証**: 既存テスト

### S46 `orchestrated.py::OrchestratedRequest`

- **変更**: `branch_id: int = Field(default=1, ge=1)` のまま、description を補強
- **検証**: OpenAPI スキーマ確認

### S47 `MultimediaService.generate_asset_pack()` の `include_if_routes` 経路記録

- **目的**: 新 `/api/branches` と並存させるため、既存の `multimedia.py:125 generate_if_routes` の **呼び出し統計** をログ追加
- **検証**: 既存挙動無変更

### S48 Episode 4 リグレッションテスト集約

- **追加**: `tests/branches/test_branch_id_propagation.py`
- **検証**: 全 `branch_id=1` 固定箇所にテスト 1 本ずつ

**Episode 4 完了条件**:
- [ ] 全マトリクス箇所で `current_branch_id` / 明示指定が優先される
- [ ] 既存テスト無劣化

---

## Episode 5: FastAPI 標準 WS + エディタ UI ベース (S49-S60)

### S49 `WS /api/branches/play/{session_id}` 雛形

- **変更ファイル**: `src/backend/routers/branches.py`
- **追加内容**: `@router.websocket("/play/{session_id}/ws")` の骨格
- **検証**: `pytest tests/branches/test_ws_connection.py::test_connect -v`

### S50 WS で `state` イベント送信

- **追加内容**: 接続時に現 state を push
- **検証**: クライアントモックで受信確認

### S51 WS で `choose` イベント受信

- **追加内容**: `{"action": "choose", "choice_id": "..."}` を受信し `make_choice` を呼ぶ
- **検証**: state push まで完走

### S52 WS で `save` / `load` イベント

- **追加内容**: `{"action": "save"|"load", "index": int}`
- **検証**: ロード後の state 一致

### S53 WS 切断時のセッションクローズ

- **追加内容**: `websocket.close()` で `status="disconnected"` に更新
- **検証**: 状態遷移テスト

### S54 WS エラーハンドリング

- **追加内容**: 不正 payload で `{"type": "error", "message": "..."}` を push
- **検証**: エラーパステスト

### S55 エディタ UI ベースライン HTML

- **変更ファイル**: `frontend/public/branches-editor.html`（新規）
- **追加内容**: ブランチ一覧とグラフ可視化の最小 HTML
- **検証**: ブラウザでロード可能

### S56 ノード一覧 API `GET /api/branches/{book_id}/nodes`

- **追加内容**: `IFRouteGraph` のノード一覧を返す
- **検証**: リスト確認

### S57 ノード作成 API `POST /api/branches/{book_id}/nodes`

- **追加内容**: 新規 `RouteNode` をグラフに追加し保存
- **検証**: DB 永続化テスト

### S58 ノード削除 API `DELETE /api/branches/{book_id}/nodes/{node_id}`

- **追加内容**: ノード削除（孤立ノード防止チェック付き）
- **検証**: 削除後グラフ整合性

### S59 グラフ整合性検証 `POST /api/branches/{book_id}/editor/validate`

- **追加内容**: 無限ループ・孤立ノード・MERGE 不正検知
- **検証**: 不正グラフで 422

### S60 エディタ UI と API の統合テスト

- **追加**: Playwright（既存構成に合わせる）で 1 本
- **検証**: ノード作成 → グラフ更新 → 一覧反映

**Episode 5 完了条件**:
- [ ] WS で双方向通信可能
- [ ] エディタ UI から CRUD 操作可能
- [ ] 整合性検証が機能

---

## Episode 6: EPUB 基本スジ + 統計 + E2E (S61-S72)

### S61 EPUB 分割出力の出力ディレクトリ決定

- **変更ファイル**: `src/backend/services/ebook_export.py`（または新規 `branch_ebook_export.py`）
- **追加内容**: `output_dir/{book_id}/branch_{branch_id}/` 構造
- **検証**: ディレクトリ作成確認

### S62 `IFRoutePlayer.export_playthrough()` → EPUB 変換器

- **追加内容**: playthrough JSON を EPUB の chapter 順に並べ替える関数
- **検証**: EPUB ファイル生成

### S63 EPUB メタデータ反映

- **追加内容**: branch 名を `dc:title` のサフィックスに
- **検証**: EPUB メタデータ読み出し

### S64 複数 EPUB の ZIP 化

- **追加内容**: 全ブランチの EPUB を 1 つの ZIP に格納
- **検証**: 展開して各 EPUB が読める

### S65 `POST /api/branches/{book_id}/export` 実装

- **追加内容**: ZIP を `Response` で返却
- **検証**: Content-Type: application/zip

### S66 EPUB 内スパイン順序の安定化

- **追加内容**: 同じ分岐なら同じ order
- **検証**: 決定論テスト

### S67 `GET /api/branches/{book_id}/stats` 実装

- **追加内容**: 選択率・平均到達ノード・滞在時間
- **検証**: 統計値テスト

### S68 stats 用集計クエリ追加

- **追加内容**: `branch_play_sessions.context_json` から集計
- **検証**: パフォーマンステスト（小規模データ）

### S69 `GET /api/branches/{book_id}/choices` 実装

- **追加内容**: 選択肢ごとの選択数
- **検証**: A/B 集計テスト

### S70 E2E テスト 1: REST フルフロー

- **追加**: `tests/branches/test_e2e_rest.py`（book 作成 → branch 作成 → fork → play → save/load → export）
- **検証**: 全工程完走

### S71 E2E テスト 2: WS フロー

- **追加**: `tests/branches/test_e2e_ws.py`（接続 → 受信 → 選択 → 切断）
- **検証**: 双方向通信完走

### S72 全体ドキュメント・OpenAPI 更新

- **変更ファイル**: `docs/api.md`, `openapi.json`
- **追加内容**: 新エンドポイントの自動取込 + `if_routes.md` セクション
- **検証**: `make openapi`（既存スクリプト）が無警告

**Episode 6 完了条件**:
- [ ] EPUB ZIP がダウンロード可能
- [ ] stats / choices 集計が返る
- [ ] E2E 2 本が通過
- [ ] OpenAPI に全エンドポイント反映

---

## 4. リスク Top5 とロールバック

| # | リスク | 兆候 | ロールバック |
|---|--------|------|------------|
| 1 | スキーマ不整合で Alembic が既存 DB で失敗 | `alembic upgrade head` で `IntegrityError` | S02/S08 の `downgrade` + DB バックアップから復元 |
| 2 | `MultimediaService.generate_asset_pack()` 互換性破綻 | 既存テスト `test_easy_mode_api.py` 失敗 | S47 のログ追加は **機能変更なし** なので revert 不要。テスト失敗時は S47 をスキップし既存パス温存 |
| 3 | EPUB リンダ検証不可（自動テスト不足） | EPUB ファイル破損 | `ebook_export.py` の既存パスへ S65 で **新関数追加のみ** 温存 |
| 4 | WebSocket 同時実行で 409 多発 | E2E WS テストで flaky | S49-S54 の WS 機能を feature flag（環境変数）で disable 可能にする |
| 5 | `branch_id=1` 残置データで path param 不在 | 既存 book で 404 多発 | S37-S48 は **デフォルト 1 維持** なので発生せず。万一発生時は S46 の `default=1` にフォールバック |

## 5. Done の 5 条件

1. 72 ステップすべて完了（`[x]` マーク）
2. `pytest` がカバレッジ 80% 以上で全通過
3. `openapi.json` に `/api/branches/*` が反映
4. 既存テスト（`test_migrations.py`, `test_easy_mode_api.py`, `test_cost_router.py` 等）が無劣化
5. デモ動作: `curl -X POST /api/branches/play -d '{"book_id":1,"branch_id":1}'` → `choose` → `export` がエラーなく完走

## 6. テスト戦略

- **ユニット**: 各ステップ完了時に最低 1 本追加
- **統合**: `tests/branches/` 配下に集約
- **E2E**: S70 / S71 の 2 本で全フロー検証
- **リグレッション**: 既存 `pytest tests/` 全件無劣化を各エピソードで実行

## 7. Low-LLM 実装メモ（全ステップ共通）

1. **既存ファイルを必ず読む**: 該当ステップの「変更ファイル」を `Read` してから `Edit` する
2. **コピペ可**: コードブロックは `Write` でそのまま書き込める完全形
3. **1 ステップ = 1 commit**: ロールバック粒度を担保
4. **依存を遡る**: 前提ステップが NG なら次ステップに着手しない
5. **検証コマンドを毎回実行**: 記載した検証手順は省略せず実行する
6. **エラーメッセージ全文を記録**: 失敗時 `git revert` だけで戻せない問題に発展させない

## 8. 凡例

- **Sxx**: ステップ番号
- **前提**: 上位依存ステップの ID（未完了なら着手不可）
- **変更ファイル**: 絶対パス（編集前に必ず `Read` する）
- **追加内容**: コピペ可能なコードブロック（擬似コード含む）
- **検証**: シェルコマンド + 期待動作
- **ロールバック**: `git revert` または Alembic `downgrade`
- **Low-LLM メモ**: 曖昧さを排除する実装者向け指示