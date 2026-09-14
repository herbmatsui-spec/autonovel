# PLAN 05: 開幕ブースト＆自動連載オーケストレーター 実装計画書（全12ステップ）

**対象**: AutoNovel v4.9.0 外部投稿・連載タスク管理基盤  
**目的**: カクヨムの日間ランキング・新着露出アルゴリズムをハックするため、公開初日の「開幕ブースト投下（3〜5話一挙投稿）」および読者のスマホ閲覧ピーク（7:30, 12:15, 19:00, 21:00）への自動分割予約連載を統制する。  
**前提**: 小型・低性能LLMでも迷わず1ステップずつ単一ファイル単位で実装・検証可能な粒度に分割。

---

## ステップ一覧

| Step | 区分 | 対象ファイル | 概要 |
| :---: | :---: | :--- | :--- |
| **1** | スキーマ | `src/models/serialization.py` (新規) | 連載スケジュール、投稿バッチ、投稿ステータスのPydanticモデル定義 |
| **2** | テスト | `tests/unit/kakuyomu/test_schedule_generator.py` (新規) | 黄金投稿スケジュール生成ロジックの単体テスト作成（TDD先行） |
| **3** | ロジック | `src/services/kakuyomu/schedule_generator.py` (新規) | 初日開幕ブースト＋ピーク時間帯自動配分アルゴリズムの実装 |
| **4** | インフラ | `src/services/kakuyomu/client_base.py` (新規) | カクヨム投稿クライアントの抽象インターフェースとモック実装 |
| **5** | テスト | `tests/unit/kakuyomu/test_playwright_client.py` (新規) | ヘッドレスブラウザによる下書き・予約投稿クライアントのテスト |
| **6** | アダプタ | `src/services/kakuyomu/playwright_client.py` (新規) | Playwrightを用いたカクヨム管理画面への自動下書き/予約登録クライアント |
| **7** | DB定義 | `src/infrastructure/database/models/serialization_job.py` (新規) | 連載タスク状態（保留・完了・失敗）を管理するSQLAlchemyテーブル |
| **8** | タスク | `src/backend/tasks/serialization_tasks.py` (新規) | Huey非同期タスクキューによるタイマー駆動投稿ジョブ |
| **9** | ルーター | `src/backend/routers/serialization.py` (新規) | 連載計画作成・即時投稿・進行状況取得FastAPIエンドポイント |
| **10** | 型定義 | `frontend/src/types/serialization.ts` (新規) | フロントエンド用連載管理TypeScriptインターフェース |
| **11** | フロント | `frontend/src/components/publishing/SerializationScheduler.tsx` (新規) | カレンダー/タイムライン形式での予約投稿状況可視化＆手動トリガーUI |
| **12** | 統合検証 | `tests/e2e/test_serialization_orchestration.py` (新規) | 30話ストックから開幕ブースト＋連載スケジュール自動配分のE2Eテスト |

---

## 各ステップの詳細仕様

### Step 1: Pydanticモデル定義 (`src/models/serialization.py`)
* **目標**: 連載スケジュールと投稿タスクの型を定義。
* **実装内容**:
  ```python
  from datetime import datetime
  from enum import Enum
  from pydantic import BaseModel, Field

  class PostStatus(str, Enum):
      SCHEDULED = "scheduled"
      POSTING = "posting"
      SUCCESS = "success"
      FAILED = "failed"

  class PostBatchItem(BaseModel):
      ep_num: int
      title: str
      scheduled_at: datetime
      status: PostStatus = PostStatus.SCHEDULED
      kakuyomu_episode_id: str | None = None
      error_message: str | None = None

  class SerializationPlanRequest(BaseModel):
      book_id: int
      start_date: datetime
      boost_episodes_count: int = Field(5, ge=3, le=10, description="初日開幕投下話数")
      daily_episodes_count: int = Field(2, ge=1, le=4, description="以降の1日あたり投稿話数")

  class SerializationPlanResponse(BaseModel):
      book_id: int
      batches: list[PostBatchItem]
  ```
* **受け入れ基準**: `mypy src/models/serialization.py` がエラーなく通ること。

---

### Step 2: スケジュール生成テスト作成 (`tests/unit/kakuyomu/test_schedule_generator.py`)
* **目標**: 初日ブーストとピーク時間帯（7:30, 12:15, 19:00, 21:00）に正しく配分されるか検証。
* **実装内容**:
  ```python
  from datetime import datetime
  from src.services.kakuyomu.schedule_generator import generate_golden_schedule

  def test_generate_golden_schedule_boost():
      start = datetime(2026, 10, 1, 10, 0)
      batches = generate_golden_schedule(total_eps=10, start_time=start, boost_count=5)
      # 初日に5話が投稿されていること
      day1_batches = [b for b in batches if b.scheduled_at.date() == start.date()]
      assert len(day1_batches) == 5
      # 第1〜3話は12:00、第4話は18:00、第5話は21:00に割り振られること
      assert day1_batches[0].scheduled_at.hour == 12
      assert day1_batches[4].scheduled_at.hour == 21
  ```
* **受け入れ基準**: テストがモジュール未定義で正しく失敗すること。

---

### Step 3: スケジュール生成ロジック (`src/services/kakuyomu/schedule_generator.py`)
* **目標**: カクヨムで最もPVが集まる黄金時間帯を自動計算する関数を実装。
* **実装内容**:
  - 初日: 12:00（第1〜3話一挙公開）→ 18:00（第4話）→ 21:00（第5話）
  - 2日目以降: 朝通勤 7:30、昼休み 12:15、夜ゴールデン 19:30、就寝前 21:30 の中から指定話数分配分。
* **受け入れ基準**: Step 2 のテストが GREEN になること。

---

### Step 4: 投稿クライアント抽象層 (`src/services/kakuyomu/client_base.py`)
* **目標**: カクヨム投稿のインターフェースとテスト用モックを定義。
* **実装内容**:
  ```python
  from abc import ABC, abstractmethod

  class IKakuyomuClient(ABC):
      @abstractmethod
      async def post_episode(self, work_id: str, title: str, body: str, reservation_time: datetime | None = None) -> str:
          """エピソードを投稿または予約し、エピソードIDを返す"""
          pass

  class MockKakuyomuClient(IKakuyomuClient):
      async def post_episode(self, work_id: str, title: str, body: str, reservation_time: datetime | None = None) -> str:
          return f"mock_ep_{hash(title)}"
  ```
* **受け入れ基準**: 型チェックが通過すること。

---

### Step 5: Playwrightクライアント単体テスト (`tests/unit/kakuyomu/test_playwright_client.py`)
* **目標**: ヘッドレスブラウザによるログイン・投稿フォーム入力ロジックの動作検証。
* **実装内容**:
  - 認証情報欠落時のエラーハンドリングテスト。
  - セレクタ操作のモックテスト。
* **受け入れ基準**: テストファイルが正常に実行できること。

---

### Step 6: Playwright連携クライアント (`src/services/kakuyomu/playwright_client.py`)
* **目標**: カクヨムのWeb UIを介して自動予約投稿を行う実クライアントを実装。
* **実装内容**:
  - `PlaywrightKakuyomuClient(email, password, headless=True)`
  - ログイン処理（Cookieセッション保持対応）。
  - エピソード新規作成ページでの本文・タイトル・予約日時の自動入力と公開ボタン押下。
* **受け入れ基準**: モック環境で例外処理が正しく動作すること。

---

### Step 7: DBモデル定義 (`src/infrastructure/database/models/serialization_job.py`)
* **目標**: 予約ジョブの状態をDB永続化するテーブルを作成。
* **実装内容**:
  - テーブル名: `serialization_jobs`
  - カラム: `id`, `book_id`, `ep_num`, `scheduled_at`, `status`, `kakuyomu_id`, `created_at`, `updated_at`
* **受け入れ基準**: SQLAlchemyモデルとしてインポートでき、テーブルメタデータが取得できること。

---

### Step 8: Huey非同期タスク (`src/backend/tasks/serialization_tasks.py`)
* **目標**: 指定日時になったら自動でエピソードを投稿するバックグラウンドタスク。
* **実装内容**:
  - `@huey.task()` デコレータを用いた `execute_scheduled_post(job_id: int)` の実装。
  - DBから本文取得 → カクヨムクライアントで投稿 → 成功時はステータスを `SUCCESS` に更新。
  - 失敗時は自動リトライ（最大3回）とログ出力。
* **受け入れ基準**: タスク関数が例外なく登録できること。

---

### Step 9: FastAPIルーター (`src/backend/routers/serialization.py`)
* **目標**: 連載機能のAPIエンドポイントを新設。
* **実装内容**:
  - `POST /api/serialization/plan`: スケジュール作成＆ジョブ登録
  - `GET /api/serialization/jobs/{book_id}`: ジョブ一覧取得
  - `POST /api/serialization/jobs/{job_id}/trigger`: 手動即時実行
* **受け入れ基準**: `TestClient` で 200 OK が返ること。

---

### Step 10: フロントエンド型定義 (`frontend/src/types/serialization.ts`)
* **目標**: TypeScript型定義を作成。
* **実装内容**:
  ```typescript
  export interface PostBatchItem {
    ep_num: number;
    title: string;
    scheduled_at: string;
    status: 'scheduled' | 'posting' | 'success' | 'failed';
    error_message?: string;
  }
  ```
* **受け入れ基準**: `npm run typecheck` が通過すること。

---

### Step 11: 自動連載スケジューラーUI (`frontend/src/components/publishing/SerializationScheduler.tsx`)
* **目標**: カレンダーまたは縦型タイムラインで連載進捗を一目で把握できるUIコンポーネント。
* **実装内容**:
  - 「開幕ブースト（初日5話）」トグルスイッチ。
  - 各話の投稿予定時間バッジと「今すぐ投稿」ボタン。
  - 失敗時のアラート表示と再試行ボタン。
* **受け入れ基準**: UIが正常にビルド・表示されること。

---

### Step 12: E2E統合テスト (`tests/e2e/test_serialization_orchestration.py`)
* **目標**: 計画作成からHueyタスク登録、モック投稿成功までの一連の流れを検証。
* **実装内容**:
  - 5話分のエピソードを含む作品に対してスケジュール作成 → タスク実行 → DBのステータスが `SUCCESS` になることをアサート。
* **受け入れ基準**: `pytest tests/e2e/test_serialization_orchestration.py` が ALL GREEN。
