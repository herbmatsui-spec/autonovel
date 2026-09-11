# 第1段階: UX・画面統合フェーズ 72ステップ詳細実装計画書
## （商用投稿予約管理・BookScore/PDCAダッシュボード・IF分岐マージ確定UI統合）

- **策定日**: 2026年9月10日
- **対象バージョン**: AutoNovel v4.5.0+
- **設計方針**: 低性能なLLMでも迷わず1ステップずつ確実に実装・検証できるよう、最小単位の作業に分割。12ステップごとに動作検証ゲート（Checkpoint）を設置。
- **総ステップ数**: 全72ステップ（6パート × 12ステップ）

---

## 📋 パート別構成概要

| パート | ステップ | テーマ | 主な対象ファイル | ステータス |
|---|---|---|---|---|
| **Part 1** | Step 1〜12 | 商用出版投稿予約・スケジュール管理のバックエンドAPI基盤強化 | `src/backend/database/models.py`<br>`src/backend/routers/commercial.py`<br>`src/backend/tasks/commercial_tasks.py` | ⏳ 未着手 |
| **Part 2** | Step 13〜24 | フロントエンド「商用投稿管理ダッシュボード」新規実装 | `frontend/src/components/commercial/`<br>`frontend/src/api/commercial.ts`<br>`frontend/src/App.tsx` | ⏳ 未着手 |
| **Part 3** | Step 25〜36 | BookScore 5次元レーダーチャート & PDCA改善推移バックエンドAPI整備 | `src/backend/routers/system.py`<br>`src/services/book_score_service.py`<br>`src/services/pdca_cycle.py` | ⏳ 未着手 |
| **Part 4** | Step 37〜48 | フロントエンド「BookScore & PDCA品質ダッシュボード」実装 | `frontend/src/components/studio/BookScoreRadarChart.tsx`<br>`frontend/src/components/studio/PDCACycleViewer.tsx` | ⏳ 未着手 |
| **Part 5** | Step 49〜60 | IFルート分岐マージの本文・世界観への確定書き戻しバックエンド実装 | `src/backend/routers/branches.py`<br>`src/services/conflict_report_service.py` | ⏳ 未着手 |
| **Part 6** | Step 61〜72 | フロントエンド マージ確定フロー統合 & 第1段階 E2E 結合検証 | `frontend/src/components/branches/MergeConflictPreview.tsx`<br>`tests/integration/test_phase1_ux_e2e.py` | ⏳ 未着手 |

---

## 🚀 Part 1: 商用出版投稿予約・スケジュール管理のバックエンドAPI基盤強化 (Step 1〜12)

### Step 1: 投稿スケジュールDBモデル `PublicationScheduleModel` の定義
- **目的**: 小説家になろう・カクヨム・Kindle等の投稿予約日時、ステータス、対象エピソード範囲を永続化するモデルを定義する。
- **対象ファイル**: `src/backend/database/models.py`
- **変更内容**:
  ```python
  class PublicationScheduleModel(Base):
      __tablename__ = "publication_schedules"
      id = Column(Integer, primary_key=True, autoincrement=True)
      book_id = Column(Integer, ForeignKey("books.id"), nullable=False, index=True)
      platform = Column(String(50), nullable=False)  # "narou", "kakuyomu", "kindle", "kobo"
      episode_range_start = Column(Integer, nullable=False, default=1)
      episode_range_end = Column(Integer, nullable=False, default=1)
      scheduled_at = Column(DateTime, nullable=False)
      status = Column(String(20), nullable=False, default="pending")  # pending, running, completed, failed, cancelled
      post_id = Column(String(100), nullable=True)
      error_message = Column(Text, nullable=True)
      created_at = Column(DateTime, default=datetime.utcnow)
      updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
  ```
- **確認コマンド**: `python -c "from src.backend.database.models import PublicationScheduleModel; print(PublicationScheduleModel.__tablename__)"`
- **完了条件**: `publication_schedules` が正常に出力されること。

### Step 2: Alembicマイグレーションスクリプト作成 (`0021_publication_schedules.py`)
- **目的**: `publication_schedules` テーブルをDBに反映するためのマイグレーションを作成する。
- **対象ファイル**: `database/alembic/versions/0021_publication_schedules.py`
- **変更内容**: `op.create_table("publication_schedules", ...)` を定義。
- **確認コマンド**: `python -m py_compile database/alembic/versions/0021_publication_schedules.py`
- **完了条件**: 構文エラーがなくコンパイルできること。

### Step 3: Pydanticスキーマ `PublicationScheduleCreate` / `PublicationScheduleResponse` 定義
- **目的**: 投稿予約APIのリクエスト・レスポンス用スキーマを定義する。
- **対象ファイル**: `src/backend/routers/commercial.py`
- **変更内容**:
  ```python
  class PublicationScheduleCreate(BaseModel):
      book_id: int = Field(..., ge=1)
      platform: str = Field(..., pattern="^(narou|kakuyomu|kindle|kobo)$")
      episode_range: tuple[int, int]
      scheduled_at: datetime
      credentials_override: dict[str, Any] | None = None

  class PublicationScheduleResponse(BaseModel):
      id: int
      book_id: int
      platform: str
      episode_range: tuple[int, int]
      scheduled_at: datetime
      status: str
      error_message: str | None = None
      created_at: datetime
  ```
- **確認コマンド**: `python -c "from src.backend.routers.commercial import PublicationScheduleCreate; print('OK')"`
- **完了条件**: スキーマがインポート可能であること。

### Step 4: 投稿スケジュール登録API `POST /commercial/schedules` の実装
- **目的**: 指定された書籍・プラットフォーム・日時の投稿予約をDBに登録するエンドポイントを追加する。
- **対象ファイル**: `src/backend/routers/commercial.py`
- **変更内容**:
  ```python
  @router.post("/schedules", response_model=PublicationScheduleResponse)
  async def create_schedule(
      req: PublicationScheduleCreate,
      db: AsyncSession = Depends(get_db),
      api_key: str = Depends(require_api_key)
  ):
      ...
  ```
- **確認コマンド**: `python -m py_compile src/backend/routers/commercial.py`
- **完了条件**: 構文エラーがないこと。

### Step 5: 投稿スケジュール一覧取得API `GET /commercial/schedules/{book_id}` の実装
- **目的**: 書籍ごとの予約一覧（過去履歴および未実行分）を取得するエンドポイントを追加する。
- **対象ファイル**: `src/backend/routers/commercial.py`
- **変更内容**: `book_id` をキーに最新の投稿スケジュール一覧をソートして返却。
- **確認コマンド**: `python -m py_compile src/backend/routers/commercial.py`
- **完了条件**: 関数が追加され正常にコンパイルできること。

### Step 6: 投稿スケジュール取消API `DELETE /commercial/schedules/{schedule_id}` の実装
- **目的**: 未実行（`pending`）の予約投稿をキャンセル（`cancelled`）または削除する。
- **対象ファイル**: `src/backend/routers/commercial.py`
- **変更内容**: `status == 'pending'` の場合のみ安全にキャンセル更新。実行中・完了済みの場合はエラーを返す。
- **確認コマンド**: `python -m py_compile src/backend/routers/commercial.py`
- **完了条件**: キャンセル処理が実装されていること。

### Step 7: 非同期投稿ワーカータスク `execute_publication_task` の新設
- **目的**: Hueyキュー経由で指定された時間に自動実行されるバックグラウンドタスクを実装する。
- **対象ファイル**: `src/backend/tasks/commercial_tasks.py` (新規作成)
- **変更内容**: `schedule_id` を受け取り、`PublicationScheduleModel` を参照して `CommercialPipeline.run` または `publish_commercial` を呼び出す。
- **確認コマンド**: `python -m py_compile src/backend/tasks/commercial_tasks.py`
- **完了条件**: タスク関数が定義され、インポートできること。

### Step 8: 投稿実行中のステータス遷移（pending → running → completed / failed）の実装
- **目的**: 実行開始時に `status="running"`、終了時に成否と `post_id` または `error_message` をDBに記録する。
- **対象ファイル**: `src/backend/tasks/commercial_tasks.py`
- **変更内容**: `try...except` でエラーを捕捉し、失敗時も確実にDBを更新するトランザクション保護。
- **確認コマンド**: `python -m py_compile src/backend/tasks/commercial_tasks.py`
- **完了条件**: 例外発生時にもDBステータスが `failed` に更新されること。

### Step 9: 投稿予約のスケジューラー連携（Huey `schedule()` 登録）
- **目的**: `POST /commercial/schedules` 登録時に、Huey の遅延タスクとして `execute_publication_task.schedule(args=(schedule.id,), eta=schedule.scheduled_at)` を呼び出す。
- **対象ファイル**: `src/backend/routers/commercial.py`
- **変更内容**: スケジュール作成成功時にタスクキューへ遅延ディスパッチ。
- **確認コマンド**: `python -m py_compile src/backend/routers/commercial.py`
- **完了条件**: タスクディスパッチ呼び出しが記述されていること。

### Step 10: 即時投稿テスト用エンドポイント `POST /commercial/schedules/{id}/run-now` の追加
- **目的**: 予約時間を待たずにテスト実行できる管理用APIを用意する。
- **対象ファイル**: `src/backend/routers/commercial.py`
- **変更内容**: 対象の `schedule_id` を直ちに実行ワーカーへ送出。
- **確認コマンド**: `python -m py_compile src/backend/routers/commercial.py`
- **完了条件**: エンドポイントが正常に追加されていること。

### Step 11: 投稿スケジュールAPIの単体テスト作成
- **目的**: スケジュールの作成・一覧取得・キャンセルの正常系・異常系をテストする。
- **対象ファイル**: `tests/unit/test_commercial_schedules_api.py` (新規作成)
- **変更内容**: テストクライアントを使用したエンドポイントテスト（モックDB使用）。
- **確認コマンド**: `pytest tests/unit/test_commercial_schedules_api.py -v`
- **完了条件**: 全テストが PASS すること。

### Step 12: 【Checkpoint 1】Part 1 動作検証と健全性確認
- **目的**: バックエンド投稿スケジュール機能の完全動作を確認する。
- **確認コマンド**: `pytest tests/unit/test_commercial_schedules_api.py tests/test_health.py -v`
- **完了条件**: すべてのテストがオールグリーン（ALL GREEN）であること。

---

## 🎨 Part 2: フロントエンド「商用投稿管理ダッシュボード」新規実装 (Step 13〜24)

### Step 13: フロントエンド型定義 `frontend/src/types/commercial.ts` の新設
- **目的**: 投稿スケジュール、プラットフォーム設定、認証ステータスのTypeScript型を定義する。
- **対象ファイル**: `frontend/src/types/commercial.ts` (新規作成)
- **変更内容**: `PublicationSchedule`, `PlatformCredentialStatus`, `ScheduleCreatePayload` を定義。
- **確認コマンド**: `npm run --prefix frontend typecheck`
- **完了条件**: 型チェックがエラーなく通過すること。

### Step 14: APIクライアント関数 `frontend/src/api/commercial.ts` の新設
- **目的**: スケジュール取得・作成・キャンセルを行うAPI呼び出し関数を実装する。
- **対象ファイル**: `frontend/src/api/commercial.ts` (新規作成)
- **変更内容**: `fetchSchedules(bookId)`, `createSchedule(payload)`, `cancelSchedule(id)`, `runScheduleNow(id)` を実装。
- **確認コマンド**: `npm run --prefix frontend typecheck`
- **完了条件**: API関数が正常にエクスポートされること。

### Step 15: プラットフォーム別アイコン・バッジコンポーネント作成
- **目的**: なろう、カクヨム、Kindle、Koboを識別する色別タグバッジコンポーネントを作成する。
- **対象ファイル**: `frontend/src/components/commercial/PlatformBadge.tsx` (新規作成)
- **変更内容**: 各プラットフォームのブランドカラー（なろう=ブルー、カクヨム=グリーン、Kindle=オレンジ等）に応じたスタイルバッジ。
- **確認コマンド**: `npm run --prefix frontend typecheck`
- **完了条件**: コンポーネントが正しく型チェックを通ること。

### Step 16: 予約投稿一覧テーブルコンポーネント作成
- **目的**: 予約日時、対象エピソード、プラットフォーム、ステータス、アクション（今すぐ実行/取消）を一覧表示するテーブル。
- **対象ファイル**: `frontend/src/components/commercial/ScheduleListTable.tsx` (新規作成)
- **変更内容**: テーブルUIとステータス（pending: 黄色, running: 青点滅, completed: 緑, failed: 赤）に応じたインジケーター表示。
- **確認コマンド**: `npm run --prefix frontend typecheck`
- **完了条件**: コンポーネントがビルドできること。

### Step 17: 新規予約投稿モーダルコンポーネント作成
- **目的**: プラットフォーム選択、エピソード範囲指定（スライダーまたは数値入力）、投稿日時指定（datetime-local）を行うモーダル。
- **対象ファイル**: `frontend/src/components/commercial/NewScheduleModal.tsx` (新規作成)
- **変更内容**: 入力バリデーション（未来の日時のみ許可、開始話数 <= 終了話数）を備えたフォーム。
- **確認コマンド**: `npm run --prefix frontend typecheck`
- **完了条件**: フォームの入力・送信ハンドラが型安全に実装されていること。

### Step 18: 投稿エラー詳細モーダルコンポーネント作成
- **目的**: ステータスが `failed` のスケジュールについて、エラー詳細ログや原因（ログイン失敗、セレクタ未検出等）を表示する。
- **対象ファイル**: `frontend/src/components/commercial/ErrorDetailModal.tsx` (新規作成)
- **変更内容**: `error_message` をコードブロックまたはアラート枠で表示し、再試行ボタンを配置。
- **確認コマンド**: `npm run --prefix frontend typecheck`
- **完了条件**: モーダルが正常にレンダリングされること。

### Step 19: 商用投稿統合パネル `CommercialPublishPanel.tsx` の構築
- **目的**: プラットフォーム連携状況、新規予約ボタン、予約一覧テーブルを束ねるメインパネルコンポーネント。
- **対象ファイル**: `frontend/src/components/commercial/CommercialPublishPanel.tsx` (新規作成)
- **変更内容**: React Query (`useQuery`, `useMutation`) を利用した自動リフレッシュと楽観的UI更新。
- **確認コマンド**: `npm run --prefix frontend typecheck`
- **完了条件**: パネルコンポーネントが正常にコンパイルされること。

### Step 20: メインナビゲーション / Studioタブへの「商用出版・投稿」タブ追加
- **目的**: Webアプリのヘッダーまたはタブ切り替えに「商用出版」を追加し、アクセス可能にする。
- **対象ファイル**: `frontend/src/App.tsx` または `frontend/src/components/studio/StudioWorkspace.tsx`
- **変更内容**: タブ一覧に `{ id: 'commercial', label: '商用投稿管理' }` を追加し、パネルをレンダリング。
- **確認コマンド**: `npm run --prefix frontend build`
- **完了条件**: Viteビルドが正常に完了すること。

### Step 21: ポーリングによる投稿進行中ステータスの自動更新
- **目的**: `running` 状態のタスクが存在する場合、5秒ごとに自動でスケジュール一覧をポーリング更新する。
- **対象ファイル**: `frontend/src/components/commercial/CommercialPublishPanel.tsx`
- **変更内容**: `refetchInterval: hasRunning ? 5000 : false` を設定。
- **確認コマンド**: `npm run --prefix frontend typecheck`
- **完了条件**: ポーリングロジックが組み込まれていること。

### Step 22: トースト通知（予約完了、キャンセル完了、エラー発生時）の統合
- **目的**: ユーザー操作の結果を画面右上にフィードバックするトースト表示を追加。
- **対象ファイル**: `frontend/src/components/commercial/CommercialPublishPanel.tsx`
- **変更内容**: 成功時・失敗時に分かりやすい日本語メッセージを表示。
- **確認コマンド**: `npm run --prefix frontend typecheck`
- **完了条件**: トースト通知が呼び出されること。

### Step 23: フロントエンド商用コンポーネントの単体テスト作成
- **目的**: モーダルの開閉、一覧テーブルのレンダリング、ボタンクリックハンドラをテスト。
- **対象ファイル**: `frontend/src/components/commercial/__tests__/CommercialPublishPanel.test.tsx` (新規作成)
- **変更内容**: `@testing-library/react` によるUI挙動検証。
- **確認コマンド**: `npm run --prefix frontend test:ci`
- **完了条件**: フロントエンドテストが通過すること。

### Step 24: 【Checkpoint 2】Part 2 動作検証とUIビルド確認
- **目的**: フロントエンドの型チェック・ビルド・テストがすべて通過することを確認。
- **確認コマンド**: `npm run --prefix frontend typecheck && npm run --prefix frontend build`
- **完了条件**: エラー0件で本番バンドルが生成されること。

---

## 📊 Part 3: BookScore 5次元レーダーチャート & PDCA改善推移バックエンドAPI整備 (Step 25〜36)

### Step 25: BookScore履歴レスポンス用 Pydantic モデル定義
- **目的**: 章ごと・再執筆サイクルごとの5次元スコア（structure, coherency, factual, visual_textual, reader_experience）の時系列データを返すスキーマを定義。
- **対象ファイル**: `src/services/book_score_service.py`
- **変更内容**:
  ```python
  class BookScoreHistoryItem(BaseModel):
      chapter_number: int
      cycle_index: int
      overall_score: float
      structure_score: float
      coherency_score: float
      factual_score: float
      visual_textual_score: float
      reader_experience_score: float
      evaluated_at: datetime
      delta_from_previous: float | None = None
  ```
- **確認コマンド**: `python -c "from src.services.book_score_service import BookScoreHistoryItem; print('OK')"`
- **完了条件**: スキーマがインポートできること。

### Step 26: DBモデルからのBookScore時系列履歴取得メソッドの実装
- **目的**: `book_scores` テーブルから指定作品・指定章の全サイクルスコアを取得するメソッドを追加。
- **対象ファイル**: `src/services/book_score_service.py`
- **変更内容**: `get_score_history(db: AsyncSession, book_id: int, chapter_number: int | None = None) -> list[BookScoreHistoryItem]`
- **確認コマンド**: `python -m py_compile src/services/book_score_service.py`
- **完了条件**: メソッドが実装されコンパイルできること。

### Step 27: PDCAサイクル詳細スナップショットモデルの拡張
- **目的**: 再執筆前の下書き、適用された `WritingDirective`、再執筆後の下書き、スコア変化をひとまとめにしたDTOを定義。
- **対象ファイル**: `src/services/pdca_cycle.py`
- **変更内容**: `PDCACycleReport` モデルに `before_text`, `after_text`, `directives_applied`, `improved_dimensions` フィールドを正式追加。
- **確認コマンド**: `python -m py_compile src/services/pdca_cycle.py`
- **完了条件**: DTOが正しく定義されていること。

### Step 28: PDCAサイクル履歴の永続化テーブル `pdca_history_snapshots` の追加
- **目的**: 各章のPDCA改善過程をDBに記録するためのテーブルモデルを定義。
- **対象ファイル**: `src/backend/database/models.py`
- **変更内容**: `PDCAHistoryModel`（book_id, chapter_number, cycle_index, score_before, score_after, diff_summary, directives_json, created_at）。
- **確認コマンド**: `python -c "from src.backend.database.models import PDCAHistoryModel; print('OK')"`
- **完了条件**: モデルが定義されていること。

### Step 29: Alembicマイグレーションスクリプト作成 (`0022_pdca_history.py`)
- **目的**: `pdca_history_snapshots` テーブルのマイグレーションを追加。
- **対象ファイル**: `database/alembic/versions/0022_pdca_history.py`
- **確認コマンド**: `python -m py_compile database/alembic/versions/0022_pdca_history.py`
- **完了条件**: コンパイルできること。

### Step 30: `ClosedLoopPDCARunner` 実行時のスナップショット自動保存フック
- **目的**: PDCAサイクルが完了するたびに `PDCAHistoryModel` へ結果を非同期保存。
- **対象ファイル**: `src/services/pdca_cycle.py`
- **変更内容**: ループ完了時に `db.add(PDCAHistoryModel(...))` を呼び出す。
- **確認コマンド**: `python -m py_compile src/services/pdca_cycle.py`
- **完了条件**: 保存ロジックが組み込まれていること。

### Step 31: APIエンドポイント `GET /api/books/{book_id}/book-scores/history` の新設
- **目的**: フロントエンドがレーダーチャートや推移グラフを描画するための履歴データを返却。
- **対象ファイル**: `src/backend/routers/system.py`
- **変更内容**: クエリパラメータ `chapter` で絞り込み可能なエンドポイントを定義。
- **確認コマンド**: `python -m py_compile src/backend/routers/system.py`
- **完了条件**: エンドポイントが追加されていること。

### Step 32: APIエンドポイント `GET /api/books/{book_id}/pdca/cycles/{chapter_number}` の新設
- **目的**: 特定の章で実行されたPDCA改善ループの詳細（Before/Afterテキスト、ディレクティブ）を返却。
- **対象ファイル**: `src/backend/routers/system.py`
- **変更内容**: `PDCAHistoryModel` を検索して整形返却。
- **確認コマンド**: `python -m py_compile src/backend/routers/system.py`
- **完了条件**: エンドポイントが追加されていること。

### Step 33: 5次元レーダー用ベンチマーク比較データ（ジャンル別平均）の算出機能
- **目的**: ユーザー作品のスコアと、同一ジャンルの目標スコア（商業基準: 85点、連載基準: 75点）を重ね合わせて表示するための基準値取得関数。
- **対象ファイル**: `src/services/book_score_service.py`
- **変更内容**: `get_genre_benchmarks(genre: str) -> dict[str, float]`
- **確認コマンド**: `python -m py_compile src/services/book_score_service.py`
- **完了条件**: 基準値マップが取得できること。

### Step 34: 履歴APIにベンチマーク比較データを統合
- **目的**: `/api/books/{book_id}/book-scores/history` のレスポンスに `genre_targets` を同梱。
- **対象ファイル**: `src/backend/routers/system.py`
- **確認コマンド**: `python -m py_compile src/backend/routers/system.py`
- **完了条件**: 正常にコンパイルできること。

### Step 35: BookScore・PDCA履歴APIの単体テスト作成
- **目的**: 履歴取得エンドポイントとPDCA詳細エンドポイントの挙動を検証。
- **対象ファイル**: `tests/unit/test_book_score_history_api.py` (新規作成)
- **確認コマンド**: `pytest tests/unit/test_book_score_history_api.py -v`
- **完了条件**: 全テストが PASS すること。

### Step 36: 【Checkpoint 3】Part 3 バックエンドAPI動作検証
- **目的**: スコア履歴・PDCAレポートAPIが正常に動作することを確認。
- **確認コマンド**: `pytest tests/unit/test_book_score_history_api.py -v`
- **完了条件**: すべてのテストがオールグリーンであること。

---

## 📈 Part 4: フロントエンド「BookScore & PDCA品質ダッシュボード」実装 (Step 37〜48)

### Step 37: レーダーチャート用 SVG描画コンポーネント `BookScoreRadarChart.tsx` の新設
- **目的**: 外部巨大ライブラリに依存せず、軽量なPure SVGで5次元（構造・一貫性・事実性・挿絵相乗・読者体験）の多角形レーダーチャートを描画する。
- **対象ファイル**: `frontend/src/components/studio/BookScoreRadarChart.tsx` (新規作成)
- **変更内容**: 5角形の軸、基準値（75点ライン/85点ライン）、現在の作品スコアのポリゴン、各頂点のラベル表示。
- **確認コマンド**: `npm run --prefix frontend typecheck`
- **完了条件**: コンポーネントがエラーなく型チェックを通過すること。

### Step 38: レーダーチャートへの「前サイクル vs 現サイクル」多重ポリゴン重ね合わせ
- **目的**: PDCA改善前（赤系半透明）と改善後（青系半透明）を重ねて表示し、どこが伸びたかを一目で視覚化。
- **対象ファイル**: `frontend/src/components/studio/BookScoreRadarChart.tsx`
- **変更内容**: `scoresBefore` と `scoresAfter` の両プロパティを受け取れるように拡張。
- **確認コマンド**: `npm run --prefix frontend typecheck`
- **完了条件**: 多重ポリゴン描画が実装されていること。

### Step 39: 章ごとのスコア推移ラインチャート `BookScoreTrendChart.tsx` の作成
- **目的**: 第1話から最新話までの総合点（BookScore Overall）の推移を折れ線グラフで表示。
- **対象ファイル**: `frontend/src/components/studio/BookScoreTrendChart.tsx` (新規作成)
- **変更内容**: 横軸＝章番号、縦軸＝0-100点、ホバー時のツールチップ表示。
- **確認コマンド**: `npm run --prefix frontend typecheck`
- **完了条件**: コンポーネントがビルドできること。

### Step 40: PDCAディレクティブ表示カード `PDCADirectiveCard.tsx` の作成
- **目的**: 「何を改善するためにどのような指示がプロンプトに注入されたか」を表示するバッジ＆リストコンポーネント。
- **対象ファイル**: `frontend/src/components/studio/PDCADirectiveCard.tsx` (新規作成)
- **変更内容**: 重要度（High/Medium/Low）、対象次元（Coherency等）、具体的な改善指示テキストのカード表示。
- **確認コマンド**: `npm run --prefix frontend typecheck`
- **完了条件**: コンポーネントが型チェックを通ること。

### Step 41: Before / After 差分ハイライトビューア `PDCADiffViewer.tsx` の作成
- **目的**: 再執筆によってテキストがどう変化したかを、インライン差分（追加: 緑、削除: 赤）で表示。
- **対象ファイル**: `frontend/src/components/studio/PDCADiffViewer.tsx` (新規作成)
- **変更内容**: 単語・文単位の簡易差分アルゴリズムまたは既存diffコンポーネントの再利用。
- **確認コマンド**: `npm run --prefix frontend typecheck`
- **完了条件**: 差分ハイライトが正常にレンダリングされること。

### Step 42: 統合品質ダッシュボードパネル `QualityDashboardModal.tsx` の作成
- **目的**: レーダーチャート、推移グラフ、PDCA差分ビューアを1つのモーダルまたは独立パネルに統合。
- **対象ファイル**: `frontend/src/components/studio/QualityDashboardModal.tsx` (新規作成)
- **変更内容**: タブ切り替え（「レーダーチャート評価」「章別スコア推移」「書き直し改善レポート」）。
- **確認コマンド**: `npm run --prefix frontend typecheck`
- **完了条件**: パネルがコンパイルできること。

### Step 43: Studioワークスペース右ペインへの「品質スコア」バッジ追加
- **目的**: 執筆エディタ画面のヘッダーまたは右ペインに現在の章のBookScore点数バッジ（例: `⭐ 82点 / 合格`）を常時表示。
- **対象ファイル**: `frontend/src/components/studio/StudioWorkspace.tsx`
- **変更内容**: クリックすると `QualityDashboardModal` が開くインタラクションを付与。
- **確認コマンド**: `npm run --prefix frontend typecheck`
- **完了条件**: バッジが表示されクリックイベントが機能すること。

### Step 44: かんたんモード（GeneratePanel）へのBookScore簡易カードの表示
- **目的**: かんたんモードで生成された第1話に対しても、総合品質スコアと商業水準達成度を表示。
- **対象ファイル**: `frontend/src/components/GeneratePanel.tsx`
- **変更内容**: 生成結果エリアに `BookScoreBadge` を組み込み。
- **確認コマンド**: `npm run --prefix frontend typecheck`
- **完了条件**: GeneratePanelが正常に型チェックを通ること。

### Step 45: スコア70点未満時の「自動改善ループ実行中」スピナー表示
- **目的**: 自動書き直しループが走っている間、どの次元を重点改善中か（例: 「論理一貫性を再調整中...」）をユーザーに明示。
- **対象ファイル**: `frontend/src/components/studio/StudioWorkspace.tsx`
- **変更内容**: SSEまたはポーリングによる改善ステータス文字列のアニメーション表示。
- **確認コマンド**: `npm run --prefix frontend typecheck`
- **完了条件**: スピナー表示が組み込まれていること。

### Step 46: 品質ダッシュボード用フロントエンドAPIクライアント関数の実装
- **目的**: `fetchBookScoreHistory(bookId, chapter)` および `fetchPDCACycles(bookId, chapter)` のAPI関数を実装。
- **対象ファイル**: `frontend/src/api/books.ts`
- **変更内容**: 型付けされたHTTP GET関数の追加。
- **確認コマンド**: `npm run --prefix frontend typecheck`
- **完了条件**: 関数がエクスポートされること。

### Step 47: レーダーチャート・品質ダッシュボードの単体テスト作成
- **目的**: レーダーチャートの頂点計算、スコア表示、モーダル開閉のテスト。
- **対象ファイル**: `frontend/src/components/studio/__tests__/BookScoreRadarChart.test.tsx` (新規作成)
- **確認コマンド**: `npm run --prefix frontend test:ci`
- **完了条件**: フロントエンドテストが PASS すること。

### Step 48: 【Checkpoint 4】Part 4 フロントエンドビルドとUI検証
- **目的**: フロントエンド全体の型チェックおよびViteビルドが通過することを確認。
- **確認コマンド**: `npm run --prefix frontend typecheck && npm run --prefix frontend build`
- **完了条件**: ビルドエラー0件であること。

---

## 🔀 Part 5: IFルート分岐マージの本文・世界観への確定書き戻しバックエンド実装 (Step 49〜60)

### Step 49: マージ確定リクエストスキーマ `BranchMergeExecuteRequest` の定義
- **目的**: 競合解決後の最終テキストと、マージ対象ブランチIDを受け取るリクエストスキーマを定義。
- **対象ファイル**: `src/backend/routers/branches.py`
- **変更内容**:
  ```python
  class ConflictResolutionChoice(BaseModel):
      chunk_index: int
      selected_source: str  # "base" | "source" | "target" | "custom"
      custom_text: str | None = None

  class BranchMergeExecuteRequest(BaseModel):
      source_branch_id: int
      target_branch_id: int
      chapter_number: int
      resolutions: list[ConflictResolutionChoice]
      final_merged_content: str | None = None
  ```
- **確認コマンド**: `python -c "from src.backend.routers.branches import BranchMergeExecuteRequest; print('OK')"`
- **完了条件**: スキーマがインポートできること。

### Step 50: 3方向マージの確定書き戻しロジック `merge_and_commit_chapter` の実装
- **目的**: ターゲットブランチの指定エピソードの本文を、解決済みマージテキストで更新する。
- **対象ファイル**: `src/services/conflict_report_service.py`
- **変更内容**: `target_chapter.content = merged_content` を安全にコミットする関数。
- **確認コマンド**: `python -m py_compile src/services/conflict_report_service.py`
- **完了条件**: 関数が実装されコンパイルできること。

### Step 51: マージコミットログの記録 `branch_merge_logs` モデル定義
- **目的**: 誰がいつどのブランチをマージし、どうコンフリクトを解決したかを記録する監査テーブル。
- **対象ファイル**: `src/backend/database/models.py`
- **変更内容**: `BranchMergeLogModel`（id, book_id, source_branch_id, target_branch_id, chapter_number, merged_at, resolved_chunks_count）。
- **確認コマンド**: `python -c "from src.backend.database.models import BranchMergeLogModel; print('OK')"`
- **完了条件**: モデルが定義されていること。

### Step 52: Alembicマイグレーションスクリプト作成 (`0023_branch_merge_logs.py`)
- **目的**: `branch_merge_logs` テーブルを作成するマイグレーションを追加。
- **対象ファイル**: `database/alembic/versions/0023_branch_merge_logs.py`
- **確認コマンド**: `python -m py_compile database/alembic/versions/0023_branch_merge_logs.py`
- **完了条件**: コンパイルできること。

### Step 53: エンドポイント `POST /api/branches/{book_id}/merge/execute` の実装
- **目的**: フロントエンドからコンフリクト解決結果を受け取り、マージを実行してDBを確定更新するAPI。
- **対象ファイル**: `src/backend/routers/branches.py`
- **変更内容**: トランザクション内で本文更新とログ記録を一括処理。
- **確認コマンド**: `python -m py_compile src/backend/routers/branches.py`
- **完了条件**: エンドポイントが追加されていること。

### Step 54: マージに伴うナレッジグラフ・世界観Bibleの同期処理
- **目的**: マージされた章に登場するキャラクター設定や状態が分岐側で変化していた場合、メインブランチのBibleへ安全に統合。
- **対象ファイル**: `src/services/conflict_report_service.py`
- **変更内容**: `sync_bible_entities_after_merge(db, book_id, source_branch_id, target_branch_id)`
- **確認コマンド**: `python -m py_compile src/services/conflict_report_service.py`
- **完了条件**: 同期関数が定義されていること。

### Step 55: マージ後のプロットツリー（章構成・要約）の自動更新
- **目的**: マージによって章の内容が変わった場合、親プロットノードの概要文（summary）を自動更新。
- **対象ファイル**: `src/services/conflict_report_service.py`
- **変更内容**: `update_plot_node_summary_after_merge(...)`
- **確認コマンド**: `python -m py_compile src/services/conflict_report_service.py`
- **完了条件**: 概要更新関数が定義されていること。

### Step 56: マージ実行のロールバック保護（トランザクション保証）
- **目的**: 本文更新、ログ記録、グラフ同期のいずれかが失敗した際、全てをロールバックして不整合を防ぐ。
- **対象ファイル**: `src/backend/routers/branches.py`
- **変更内容**: `async with db.begin():` によるアトミック実行。
- **確認コマンド**: `python -m py_compile src/backend/routers/branches.py`
- **完了条件**: ロールバック機構が組み込まれていること。

### Step 57: ブランチステータスの更新（合流済みフラグ: `merged`）
- **目的**: 全章のマージが完了したソースブランチのステータスを `merged` に更新し、UI上で合流済みと分かるようにする。
- **対象ファイル**: `src/backend/routers/branches.py`
- **確認コマンド**: `python -m py_compile src/backend/routers/branches.py`
- **完了条件**: フラグ更新処理が実装されていること。

### Step 58: EventBus への `branch.merged` イベント発行
- **目的**: マージ完了時にイベントを発行し、リアルタイム通知やキャッシュ破棄をトリガー。
- **対象ファイル**: `src/backend/routers/branches.py`
- **変更内容**: `event_bus.publish("branch.merged", {"book_id": book_id, ...})`
- **確認コマンド**: `python -m py_compile src/backend/routers/branches.py`
- **完了条件**: イベント発行が記述されていること。

### Step 59: マージ確定APIの単体・結合テスト作成
- **目的**: コンフリクト解決後の確定マージ実行APIをモックデータで検証。
- **対象ファイル**: `tests/unit/test_branch_merge_execute_api.py` (新規作成)
- **確認コマンド**: `pytest tests/unit/test_branch_merge_execute_api.py -v`
- **完了条件**: 全テストが PASS すること。

### Step 60: 【Checkpoint 5】Part 5 バックエンドマージ確定動作検証
- **目的**: マージAPIとDB更新の整合性を確認。
- **確認コマンド**: `pytest tests/unit/test_branch_merge_execute_api.py -v`
- **完了条件**: すべてのテストがオールグリーンであること。

---

## 🚀 Part 6: フロントエンド マージ確定フロー統合 & 第1段階 E2E 結合検証 (Step 61〜72)

### Step 61: フロントエンド マージ確定APIクライアント関数 `executeMerge` の実装
- **目的**: バックエンドの `POST /api/branches/{book_id}/merge/execute` を呼び出すTypeScript関数を追加。
- **対象ファイル**: `frontend/src/api/branches.ts`
- **変更内容**: `executeBranchMerge(bookId, payload: BranchMergeExecuteRequest)` を実装。
- **確認コマンド**: `npm run --prefix frontend typecheck`
- **完了条件**: 型チェックを通過すること。

### Step 62: `MergeConflictPreview.tsx` の「マージを実行」ボタンのAPI結線
- **目的**: 全チャンクの競合解決が完了した時点で活性化する「マージを確定して反映」ボタンにクリックハンドラを結線。
- **対象ファイル**: `frontend/src/components/branches/MergeConflictPreview.tsx`
- **変更内容**: `executeBranchMerge` を呼び出し、ローディング中はボタンを非活性化。
- **確認コマンド**: `npm run --prefix frontend typecheck`
- **完了条件**: ボタンにハンドラが結線されていること。

### Step 63: マージ完了時のトースト通知と画面リフレッシュ
- **目的**: マージ確定が成功した際、成功トースト（「第X章のマージが完了しました」）を表示し、エディタ本文を最新に更新。
- **対象ファイル**: `frontend/src/components/branches/MergeConflictPreview.tsx`
- **変更内容**: `queryClient.invalidateQueries({ queryKey: ['chapters', bookId] })` を呼び出す。
- **確認コマンド**: `npm run --prefix frontend typecheck`
- **完了条件**: キャッシュ無効化と通知が実装されていること。

### Step 64: 分岐ツリー可視化（`BranchTree.tsx`）における「マージ合流」エッジの描画
- **目的**: 合流（マージ）したブランチからターゲットブランチへの合流矢印（破線または別色）を React Flow 上で視覚表示。
- **対象ファイル**: `frontend/src/components/branches/BranchTree.tsx`
- **変更内容**: `edge.type = 'smoothstep'` および `edge.style = { strokeDasharray: '5,5', stroke: '#10B981' }`
- **確認コマンド**: `npm run --prefix frontend typecheck`
- **完了条件**: 合流エッジのスタイリングが追加されていること。

### Step 65: マージコンフリクト解決状態のローカルストレージ一時保存
- **目的**: 誤ってモーダルを閉じてしまっても、チャンクごとの解決選択（Base/Source/Target）が失われないよう自動下書き保存。
- **対象ファイル**: `frontend/src/components/branches/MergeConflictPreview.tsx`
- **変更内容**: `localStorage.setItem('merge_draft_' + bookId, ...)`
- **確認コマンド**: `npm run --prefix frontend typecheck`
- **完了条件**: 下書き復元ロジックが実装されていること。

### Step 66: マージ確定フローのフロントエンド統合テスト作成
- **目的**: チャンク選択 → マージ実行ボタン押下 → API呼び出し → モーダルクローズの流れをテスト。
- **対象ファイル**: `frontend/src/components/branches/__tests__/MergeConflictPreview.test.tsx` (新規作成)
- **確認コマンド**: `npm run --prefix frontend test:ci`
- **完了条件**: テストが PASS すること。

### Step 67: 第1段階 包括的 E2E 結合テスト 1（商用投稿予約 〜 実行フロー）
- **目的**: API経由で書籍作成 → 投稿スケジュール登録 → 即時実行 → ステータス完了更新を一気通貫でテスト。
- **対象ファイル**: `tests/integration/test_phase1_commercial_e2e.py` (新規作成)
- **確認コマンド**: `pytest tests/integration/test_phase1_commercial_e2e.py -v`
- **完了条件**: E2Eテストが PASS すること。

### Step 68: 第1段階 包括的 E2E 結合テスト 2（BookScore履歴 〜 レーダーデータ取得）
- **目的**: 本文執筆 → PDCA再執筆実行 → BookScore履歴APIでBefore/Afterデータが正しく取得できることをテスト。
- **対象ファイル**: `tests/integration/test_phase1_bookscore_pdca_e2e.py` (新規作成)
- **確認コマンド**: `pytest tests/integration/test_phase1_bookscore_pdca_e2e.py -v`
- **完了条件**: E2Eテストが PASS すること。

### Step 69: 第1段階 包括的 E2E 結合テスト 3（IF分岐作成 〜 マージ確定フロー）
- **目的**: mainからブランチ分岐 → 別内容を執筆 → マージプレビュー → マージ確定実行 → 本文反映をテスト。
- **対象ファイル**: `tests/integration/test_phase1_branch_merge_e2e.py` (新規作成)
- **確認コマンド**: `pytest tests/integration/test_phase1_branch_merge_e2e.py -v`
- **完了条件**: E2Eテストが PASS すること。

### Step 70: フロントエンド & バックエンド全結合ビルド検証
- **目的**: 本番ビルドアーティファクトの生成と静的アセット整合性確認。
- **確認コマンド**: `npm run --prefix frontend build && python -m py_compile src/backend/server.py`
- **完了条件**: 両方ともエラー0件で終了すること。

### Step 71: コードベース全体のクリーンアップとリント検証
- **目的**: 未使用importの削除、インポート順序の整正、型アノテーションの確認。
- **確認コマンド**: `python -m ruff check src/ tests/ && npm run --prefix frontend lint`
- **完了条件**: リントエラーが0件であること。

### Step 72: 【Final Gate】第1段階 完了総合検証（100% ALL GREEN）
- **目的**: 第1段階で追加・改修された全テストスイートおよび既存の基幹テストを一括実行し、回帰がないことを確認。
- **確認コマンド**: `pytest tests/unit/test_commercial_schedules_api.py tests/unit/test_book_score_history_api.py tests/unit/test_branch_merge_execute_api.py tests/integration/test_phase1_commercial_e2e.py tests/integration/test_phase1_bookscore_pdca_e2e.py tests/integration/test_phase1_branch_merge_e2e.py -v -o "addopts="`
- **完了条件**: すべてのテストがオールグリーン（ALL GREEN）であること。
