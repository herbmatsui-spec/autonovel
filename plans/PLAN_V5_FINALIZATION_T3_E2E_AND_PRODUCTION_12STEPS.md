# AutoNovel v5系完成化 実装計画書【T3】
# 「かんたんモード ⇄ 上級者Studio」E2E完走性と本番運用の確立（リグレッション防止含む）

- **文書ID**: PLAN_V5_FINALIZATION_T3_E2E_AND_PRODUCTION_12STEPS
- **作成日**: 2026-09-25
- **対象バージョン**: AutoNovel v5.2.0 (v5系最終完成形)
- **関連ドキュメント**: [PHASE_ROADMAP_MASTER.md](file:///e:/hhh/plans/PHASE_ROADMAP_MASTER.md), [EASY_MODE_FLOW.md](file:///e:/hhh/docs/EASY_MODE_FLOW.md)

---

## 1. 概要と目的

本計画書は、AutoNovel の核となるユーザー体験である**「かんたんモード（初心者・高速生成）」から「上級者Studio（本格執筆・推敲・設定管理）」へのシームレスな移行**、および**「ワンクリック納品（ZIP / EPUB / 投稿サイト形式）」**の完走性を完全に担保し、ローカル（SQLite）と本番（Docker/PostgreSQL）の二刀流稼働を確立するための実行計画書です。

これまで個別に開発されてきた「企画ガチャ」「逆算プロット」「二段階プロット（Coarse-to-Fine）執筆」「TipTapエディタ」「次話AI提案」「納品パッケージ生成」の各コンポーネントが、実データを用いて最初から最後までエラーなく流れることを保証します。

本計画では、データ連携のスキーマ整合、エクスポート品質の担保、実行基盤の疎通確認を実施し、さらに**「E2Eワークフローおよびストレージ等価性を保証するリグレッション防止テスト」**を整備します。

---

## 2. 12の実行ステップ

```
[スキーマ・昇格疎通]          [Studio機能・納品検証]                                  [E2Eリグレッション防止]
Step 1: 出力/受入スキーマ整合 ──► Step 4: TipTapエディタ同期 ──► Step 7: 投稿/EPUB整形 ──► Step 10: E2Eシークエンステスト
Step 2: Studio昇格API強化     ──► Step 5: 次話AI展開提案     ──► Step 8: ローカル起動検証 ──► Step 11: ストレージ等価性テスト
Step 3: 設定/グラフ自動展開   ──► Step 6: 納品ZIP生成検証     ──► Step 9: Docker本番構成検証──► Step 12: フロントUIスモークテスト
```

### Step 1: かんたんモード出力と Studio 受入データスキーマの完全整合
- **対象ファイル**:
  - [src/schemas/easy_mode.py](file:///e:/hhh/src/schemas/easy_mode.py)
  - [src/backend/database/models.py](file:///e:/hhh/src/backend/database/models.py)
  - [frontend/src/types/wizard.ts](file:///e:/hhh/frontend/src/types/wizard.ts)
- **作業内容**:
  1. かんたんモードで生成されるデータ（企画コンセプト、主人公・ヒロイン属性、逆算プロット 4 ステップ、生成本文、次話フック）の Pydantic 出力スキーマを定義。
  2. Studio モードで必要とされる `Book`、`Chapter`、`Character`、`PlotNode` の各 DB モデルおよびフロントエンド TypeScript 型との過不足・名前の不一致を解消。
- **検証コマンド**:
  ```powershell
  npm --prefix frontend run typecheck
  ```

---

### Step 2: かんたんモードから Studio への「昇格（Promote）」API および永続化ハンドラーの疎通強化
- **対象ファイル**:
  - [src/backend/routers/wizard.py](file:///e:/hhh/src/backend/routers/wizard.py)
  - [src/domain/writing/coordinator.py](file:///e:/hhh/src/domain/writing/coordinator.py)
  - [frontend/src/pages/WizardWorkflowPage.tsx](file:///e:/hhh/frontend/src/pages/WizardWorkflowPage.tsx)
- **作業内容**:
  1. ウィザード画面で執筆が完了した直後に「上級者Studioへ昇格」ボタンを押下した際、セッションデータを DB に永続保存し、新設された `book_id` を返す `/api/wizard/promote` エンドポイントを強化。
  2. 昇格時に `state_token` やプロジェクトメタデータが確実に引き継がれることを確認。
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/unit/test_wizard_flow.py -v
  ```

---

### Step 3: Studio 内でのキャラクター設定・ナレッジグラフ・伏線管理への自動データ展開
- **対象ファイル**:
  - [src/services/rag/relational_memory.py](file:///e:/hhh/src/services/rag/relational_memory.py)
  - [frontend/src/components/studio/KnowledgeGraphPanel.tsx](file:///e:/hhh/frontend/src/components/studio/KnowledgeGraphPanel.tsx)
- **作業内容**:
  1. かんたんモードから昇格した作品データが、Studio の「設定資料パネル」および「ナレッジグラフ（関係性図）」へ初期ノード・エッジとして即座に展開される処理を実装。
  2. 伏線トラッカー（Foreshadowing Tracker）にかんたんモードで設定した伏線キーワードが未回収フラグ付きで登録されることを確認。
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/unit/test_relational_memory.py -v
  ```

---

### Step 4: Coarse-to-Fine 二段階プロットと Studio エディタ（TipTap）の双方向編集同期
- **対象ファイル**:
  - [frontend/src/components/studio/TipTapEditor.tsx](file:///e:/hhh/frontend/src/components/studio/TipTapEditor.tsx)
  - [src/domain/writing/jit_expander.py](file:///e:/hhh/src/domain/writing/jit_expander.py)
- **作業内容**:
  1. Studio の本文エディタ（TipTap）で執筆・加筆した内容が、自動保存（オートセーブ）経由で `PlotMicroBlueprint` のビート情報と齟齬を起こさずに更新される同期ロジックを検証。
  2. エディタ内での文字数カウント、ルビ表示、会話文率のリアルタイム計算の安定動作を確認。
- **検証コマンド**:
  ```powershell
  npm --prefix frontend run test -- src/components/studio/TipTapEditor.test.tsx --run
  ```

---

### Step 5: 「次話 AI 展開提案（Next Episode Directives）」の実動推論と反映
- **対象ファイル**:
  - [src/agents/planner_agent.py](file:///e:/hhh/src/agents/planner_agent.py)
  - [frontend/src/components/studio/NextEpisodeSuggestionPanel.tsx](file:///e:/hhh/frontend/src/components/studio/NextEpisodeSuggestionPanel.tsx)
- **作業内容**:
  1. 現在の章の本文と伏線状況から、AI が「王道展開」「波乱展開」「キャラクター深掘り展開」の 3 案を提示する推論エンドポイントの実動確認。
  2. 提案された案をユーザーが選択した際、次話の `EpisodeMacroSkeleton` へワンクリックで組み込まれる導線を検証。
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/unit/test_next_episode_suggestions.py -v
  ```

---

### Step 6: ワンクリック納品パッケージ（ZIP 生成）のファイル破損防止と文字コード検証
- **対象ファイル**:
  - [src/services/export_service.py](file:///e:/hhh/src/services/export_service.py)
  - [src/backend/routers/export.py](file:///e:/hhh/src/backend/routers/export.py)
- **作業内容**:
  1. 納品パッケージ（`01_本文.txt`, `02_設定集.txt`, `03_プロット概要.txt`, `04_データダンプ.json`）の ZIP 生成処理を検証。
  2. Windows のメモ帳で文字化けしない UTF-8 (BOM付き) / CRLF 改行の整合性、および ZIP 内パス名の日本語文字化け防止（CP437 vs UTF-8 フラグ）を確認。
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/unit/test_export_zip.py -v
  ```

---

### Step 7: 各投稿プラットフォーム向け整形および縦書き EPUB 3 のフォーマット検証
- **対象ファイル**:
  - [src/services/publishers/formatters.py](file:///e:/hhh/src/services/publishers/formatters.py)
  - [src/services/ebook/epub_generator.py](file:///e:/hhh/src/services/ebook/epub_generator.py)
- **作業内容**:
  1. 「小説家になろう」「カクヨム」「アルファポリス」向けのルビ記号（`|漢字《ルビ》` 等）および傍点・前書き・後書きの自動整形ルールを検証。
  2. EPUB 3 規格に準拠した縦書き（`writing-mode: vertical-rl`）電子書籍ファイルの出力と、EPUB リーダーでの表示崩れがないことを確認。
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/unit/test_platform_formatters.py -v
  ```

---

### Step 8: Windows ローカル起動スクリプトの自動検査と堅牢化
- **対象ファイル**:
  - [アプリ起動_ローカル.bat](file:///e:/hhh/アプリ起動_ローカル.bat)
  - [アプリ停止.bat](file:///e:/hhh/アプリ停止.bat)
  - [scripts/start_local.ps1](file:///e:/hhh/scripts/start_local.ps1)
  - [scripts/check_env.py](file:///e:/hhh/scripts/check_env.py)
- **作業内容**:
  1. `アプリ起動_ローカル.bat` を実行した際、`.venv` の存在確認、SQLite DB の安全な Alembic マイグレーション適用、Uvicorn・Huey・Vite のポート競合自動回避・起動が 100% 成功することを確認。
  2. `アプリ停止.bat` による孤立プロセスの確実なキル（ポート 8200, 5173）を確認。
- **検証コマンド**:
  ```powershell
  powershell -ExecutionPolicy Bypass -File scripts/start_local.ps1 -DryRun
  ```

---

### Step 9: 本番 Docker 環境での疎通・マイグレーション・ヘルスチェック検証
- **対象ファイル**:
  - [docker-compose.prod.yml](file:///e:/hhh/docker-compose.prod.yml)
  - [Dockerfile.prod](file:///e:/hhh/Dockerfile.prod)
- **作業内容**:
  1. PostgreSQL 16 + Redis 7 + ChromaDB のコンテナ立ち上げ時、環境変数（パスワード、シークレット等）が安全に注入されることを確認。
  2. FastAPI のヘルスチェック（`/health`）が実 DB への疎通を確認した上で HTTP 200 OK を返し、未接続時に 503 を返す本番仕様を満たしていることを検証。
- **検証コマンド**:
  ```powershell
  docker compose -f docker-compose.prod.yml config
  ```
  *(構文エラーや環境変数欠落がないこと)*

---

### Step 10: 【リグレッション防止テスト】かんたんモード→Studio昇格→納品ZIP E2Eシークエンステストの実装
- **新規作成ファイル**:
  - `tests/e2e/test_v5_workflow_e2e.py`
- **テスト設計**:
  * **テスト1**: `test_full_creation_to_zip_delivery_flow`
    * 企画ガチャAPI呼び出し ──► プロットビルダー生成 ──► 本文生成 ──► Studio昇格API呼び出し ──► 本文微修正 ──► ZIP納品パッケージダウンロード、という一連の HTTP シークエンスをテストクライアントで自動走破し、ZIP の解凍・各ファイル内容の妥当性をアサート。
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/e2e/test_v5_workflow_e2e.py -v
  ```

---

### Step 11: 【リグレッション防止テスト】SQLite / PostgreSQL ストレージ等価性テストの実装
- **新規作成ファイル**:
  - `tests/e2e/test_v5_storage_parity.py`
- **テスト設計**:
  * **テスト1**: `test_sqlite_and_postgres_model_parity`
    * Alembic マイグレーションが SQLite（ローカル）と PostgreSQL（本番）の両方のデータベースダイアレクトに対してエラーなく適用でき、全テーブル・全カラムの型が互換であることをアサート。
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/e2e/test_v5_storage_parity.py -v
  ```

---

### Step 12: 【リグレッション防止テスト】フロントエンド状態引き継ぎ・UI スモークテストの実装
- **新規作成ファイル**:
  - `frontend/src/tests/workflow_promotion.test.tsx`
- **テスト設計**:
  * **テスト1**: `test_wizard_to_studio_state_transition`
    * React Testing Library を使用し、ウィザードの最終画面で「上級者Studioへ昇格」ボタンをクリックした際、ルーティングが `/studio/:bookId` へ切り替わり、本文エディタおよびキャラクター一覧に生成データが正しくマウントされることをアサート。
- **検証コマンド**:
  ```powershell
  npm --prefix frontend run test -- src/tests/workflow_promotion.test.tsx --run
  ```

---

## 3. 完了の定義 (Definition of Done)
1. かんたんモードからStudioモードへのデータ昇格、本文編集、ZIP/EPUB納品パッケージ出力までの全導線が実データで完走する。
2. Windowsワンクリック起動スクリプトおよび本番Docker構成の双方がエラーなく立ち上がる。
3. 新設された 3 つのリグレッション防止テストスイート（`test_v5_workflow_e2e.py`, `test_v5_storage_parity.py`, `workflow_promotion.test.tsx`）が常時合格する。
