# かんたんモード E2E フロー検証 - 厳し評価レポート

**実施日**: 2026-09-07
**対象フロー**: アプリ起動 → かんたんモードで1作品作成 → 納品 (ZIP エクスポート)
**評価方針**: コードベースから各段階の実装を精査し、実際に動作するか・途中で詰まるか を厳しく検証

---

## エグゼクティブサマリ

**結論**: フロー全体としては繋がっているが、**実際には途中で失敗・想定外の挙動が発生する箇所が複数あり**、**初回ユーザーが「ストレスなく」1作品完成させるハードルは高い**。

| 段階 | 想定成功率 | 主な詰まりポイント |
|------|------------|------------------|
| 1. アプリ起動 | 60% | Redis / DB / ChromaDB 等の外部依存 |
| 2. UI で入力 | 70% | フロントエンドが起動していない問題 |
| 3. 1作品作成（かんたんモード） | 40% | LLM API キー未設定・ジャンル→プリセット解決失敗 |
| 4. ZIP 納品 | 75% | book_id 0 / 存在しない book でのフォールバック |
| **全体 E2E** | **約15%** | 上記すべての積算 |

---

## 1. アプリ起動フェーズ

### 1.1 起動経路（2系統）

#### A. ローカル開発（[`scripts/start_local.py`](autonovel/scripts/start_local.py)）
- **3プロセス同時起動**: バックエンド (uvicorn :8200) + Huey ワーカー + フロントエンド (Vite :5173)
- 問題点：
     - **`frontend/` ディレクトリが存在しないか未完成の場合に即座に起動失敗**（[`start_local.py:15-17`](autonovel/scripts/start_local.py:15) で `FRONTEND_DIR` を取得、`subprocess.Popen` が失敗しても検知しない）
     - Huey ワーカーが DB ファイルロックを取得できないと、他プロセスと競合する可能性
     - `p.poll()` 監視はあるが、**失敗プロセスの自動再起動ロジックがない**（[`start_local.py:71`](autonovel/scripts/start_local.py:71) で警告表示のみ）

#### B. Docker（[`start_docker.bat`](autonovel/start_docker.bat) / `docker-compose.yml`）
- PostgreSQL + Redis + ChromaDB + アプリ
- 問題点：
     - 4コンテナ同時に起動するため、**マシンスペックが低いとメモリ不足**（最低8GB推奨だがREADME記載なしの可能性）
     - DBマイグレーション `alembic upgrade head` をいつ実行するかが不明確（コンテナ起動時に自動実行？手動？）

### 1.2 環境変数の落とし穴

[`config.py:62`](autonovel/src/backend/config.py:62) で `LLM_PROVIDER` のデフォルトが **`"mock"`** ：

```python
LLM_PROVIDER: Literal["openai", "gemini", "mock", "claude", "ollama", "vllm"] = "mock"
```

- mock プロバイダだと**かんたんモードは動作するが、品質監査は形骸化**（常にスコア50点を返すだけ）
- `.env.example:6` では `LLM_PROVIDER=openai` がデフォルト記載 → **初回起動時に OPENAI_API_KEY が空だと [`factory.py:58-62`](autonovel/src/services/llm/factory.py:58) で `RuntimeError`**
- **`OPENAI_BASE_URL` も未設定だと OpenAI 本体にアクセス** → 課金発生

### 1.3 依存サービスの起動順序問題

[`config.py:42-43`](autonovel/src/backend/config.py:42) で Huey バックエンドが `sqlite` デフォルト：
- デフォルトでは SQLite なので Redis 不要 → 良い
- 一方 [`config.py:88`](autonovel/src/backend/config.py:88) で `ENABLE_GRAPHRAG: bool = True` デフォルト
- **GraphRAG 有効時は pgvector + Apache AGE が必要** → デフォルト設定だとローカル起動で即座にエラー

---

## 2. UI 入力フェーズ

### 2.1 ルーターの登録問題

[`server.py:72-74`](autonovel/src/backend/server.py:72) で：
```python
app.include_router(easy_mode.router, prefix="/easy_mode", tags=["easy_mode"])
if settings.APP_ENV == "development":
    app.include_router(easy_mode.router, prefix="/api/easy-mode", tags=["easy-mode"])
```

- **`/api/easy-mode` が development 環境でしか公開されない**
- フロントエンドが本番モード（`APP_ENV=production`）でビルドされている場合、APIパスが不一致 → 404
- フロントエンドの API ベース URL がどう設定されているか不明（コードベース未確認のため推測）

### 2.2 `/easy_mode/generate` の実装

[`easy_mode.py:226-294`](autonovel/src/backend/routers/easy_mode.py:226) の `generate_content`：

- **入力の `current_chapter` は "現在の章" の本文** → 「初回の章を新規生成する」用途ではなく、「既存章の続きを書く」用途
- **章単位の対話型自動生成** → 「作品全体を1回で作る」かんたんモードとは別物
- **かんたんモード本体（[EasyModeWorkflow](autonovel/src/backend/workflows/easy_mode_workflow.py)）を呼び出すエンドポイントが見当たらない**

#### 🚨 **重大な発見**

`/easy_mode/generate` の処理内容は **`process_chapter`（[`digest_service.py`](autonovel/src/services/digest_service.py) を経由）を呼び出すだけ**で、`EasyModeWorkflow` を起動するエンドポイントが**見つからない**。

かんたんモードの本体ワークフローを起動するには、**[`auto_workflow_pipeline.py`](autonovel/src/services/auto_workflow_pipeline.py) や [`full_auto_workflow.py`](autonovel/src/backend/workflows/full_auto_workflow.py) に対応するエンドポイントが必要**ですが、現状の routers 登録を見る限り **直接的な起動エンドポイントが存在しない**可能性があります。

### 2.3 ジャンル→プリセット解決

[`easy_mode.py:31-43`](autonovel/src/backend/routers/easy_mode.py:31) で `GENRE_TO_PRESET` マッピング：

```python
GENRE_TO_PRESET = [
    ("ざまぁ", "zarma"),
    ("令嬢", "aku_reijo"),
    ...
]
```

- **日本語のキーワード部分一致**で解決するヒューリスティック
- 「異世界転生」と「転生もの」は別ジャンル扱い → 期待と違うプリセットが適用される可能性
- ユーザーが「ファンタジー」と入力すると **どの preset にもマッチせず `None`** が返り、スタイル未定義で進行

---

## 3. 1作品作成（かんたん模式）フェーズ

### 3.1 パイプライン構成

[`auto_workflow_pipeline.py:146-172`](autonovel/src/services/auto_workflow_pipeline.py:146) でかんたんモードのパイプラインは：
1. **InferenceStep** - 1行プロンプトから推論
2. **PlanStep** - 企画生成
3. **WriteStep** - 本文執筆
4. **AuditRewriteStep** - 監査リライト（SpiceGuard 有効時）
5. **MarketingStep** - タイトル・キャッチコピー生成
6. **PackageStep** - 納品パッケージ準備

問題点：
- **CatharsisAnalysisStep（カタルシス分析）が無効**（[`auto_workflow_pipeline.py:158`](autonovel/src/services/auto_workflow_pipeline.py:158) のコメントで明記：「EasyMode では未実装」）
- **IllustrationStep（挿絵生成）が無効**（[`auto_workflow_pipeline.py:158`](autonovel/src/services/auto_workflow_pipeline.py:158) で「挿絵生成は無効」明記）
- かんたんモードの名に反し、**品質保証の主要機能がオミットされている**

### 3.2 InferenceStep の問題

[`auto_workflow_pipeline.py:27-61`](autonovel/src/services/auto_workflow_pipeline.py:27)：
- `ctx.user_prompt` がある時のみ推論を実行
- **失敗時のハンドリング**: 「⚠️ 自動強化に失敗しましたが、既存のパラメータで続行」と警告を出すだけで、**コンテキストがほぼ空のまま PlanStep に進む**
- `user_prompt` が空の場合、**infer_easy_mode_params は呼ばれず**、デフォルト値（`genre="ファンタジー"` 等）で進行

### 3.3 PlanStep の失敗ケース

[`pipeline_steps.py:62-169`](autonovel/src/services/pipeline_steps.py:62)：

- `engine.planner.create_hegemony_plan(...)` の戻り値が `(book_id, bible)`
- **bible 健全性チェック (`audit_bible_completeness`) が False なら False を返却**
- パイプライン本体 [`auto_workflow_pipeline.py:79-95`](autonovel/src/services/auto_workflow_pipeline.py:79) で `not success` → `FullAutoWorkflowResult(status="failed_integrity_check")` で**即終了**
- **失敗時に `failed_episodes` は空のまま** → ユーザーに何が失敗したか伝わらない

### 3.4 WriteStep の LLM 依存性

[`pipeline_steps.py:177-220`](autonovel/src/services/pipeline_steps.py:177)：

- `engine.writer.generate_episodes_pipeline` を呼び出し
- **LLM API キーが未設定だと `RuntimeError` で例外**
- **max_retries=0**（[`pipeline_param_mapper.py:79`](autonovel/src/services/pipeline_param_mapper.py:79) のかんたんモード設定）
- リトライなしで**1発勝負**、途中で失敗したら**ユーザーは再投入が必要**

### 3.5 LLM プロンプト容量

- かんたんモードの **1話あたりデフォルト文字数 2000**（[`easy_mode_workflow.py:39`](autonovel/src/backend/workflows/easy_mode_workflow.py:39)）
- 8話 default（[`auto_workflow_pipeline.py:148`](autonovel/src/services/auto_workflow_pipeline.py:148)）
- 合計 16000 字生成のため、**最低でも 30,000〜50,000 トークンのLLM消費**
- **GPT-4o-mini でも数分、Claude 3.5 Sonnet で1〜2分**の生成時間
- **ユーザーは進捗が見えない**（UIの stream 実装は [`backend/routers/streaming.py`](autonovel/src/backend/routers/streaming.py) にあるが、SSE接続が必要）

### 3.6 DB マイグレーション

- `easy_mode_drafts` テーブルが alembic で追加されている（[`0004_add_ai_assistant_config.py`](autonovel/src/backend/alembic/versions/0004_add_ai_assistant_config.py)）
- **しかしマイグレーションが未実行の状態で起動すると、[`repositories/easy_mode_draft_repository.py`](autonovel/src/backend/database/repositories/easy_mode_draft_repository.py) が `relation does not exist` エラー**
- 初回起動手順で `alembic upgrade head` を実行する手順が README に明記されているか不明

---

## 4. 納品（エクスポート）フェーズ

### 4.1 エクスポートエンドポイント

[`easy_mode.py:297-332`](autonovel/src/backend/routers/easy_mode.py:297) の `/easy_mode/export/{book_id}`：

```python
agent = MarketingAgent(repo=repo)
zip_bytes, zip_filename = await agent.create_export_package(book_id)
```

[`marketing.py:55-129`](autonovel/src/agents/marketing.py:55) の実装：
- `book_id` に対応する Book が DB に**存在しない場合 `ValueError("作品が見つかりません。")` で例外**
- しかし [`easy_mode.py:302-306`](autonovel/src/backend/routers/easy_mode.py:302) のコメントには「**book_id に対応する作品が DB に存在しなくてもフォールバックデータで ZIP を生成して返却する仕様 (TC-12 参照)**」とある
- → **コメントと実装が矛盾**！実装は `raise ValueError` しており、フォールバックは機能していない

### 4.2 エクスポート ZIP の内容

[`marketing.py:70-126`](autonovel/src/agents/marketing.py:70) で生成される ZIP：
- `01_本文.txt` - 全エピソードを結合したテキスト
- `02_キャラクター・世界観設定集.txt`
- `03_プロット概要.txt`
- `04_データダンプ.json`

問題点：
- **EPUB / PDF / MOBI は生成されない**（[`multimedia_service.py`](autonovel/src/backend/multimedia_service.py) や [`easy_mode/phase3/ebook_export.py`](autonovel/src/easy_mode/phase3/ebook_export.py) は別ルート）
- **かんたんモードの納品は「テキストファイル4本」だけ** → 商業出版向けには不十分
- 表紙画像も含まれない

### 4.3 file_id=1 の問題

[`easy_mode.py:459`](autonovel/src/backend/routers/easy_mode.py:459) の `/export-with-data`：
- `book_id: int = 1` が**デフォルト値**
- パラメータ指定なしで叩くと book_id=1 で固定 → 他ユーザーの作品を上書きするリスク
- 認証ミドルウェアがない（後述）

---

## 5. セキュリティ・認可

### 5.1 認証の弱さ

[`config.py:53-54`](autonovel/src/backend/config.py:53)：
```python
AUTH_DISABLED: bool = False
ALLOWED_API_KEYS: str = ""
```

- **デフォルトで `AUTH_DISABLED=False`** だが、API キーが空
- 実装を見ると [`server.py`](autonovel/src/backend/server.py) には認証ミドルウェアが見当たらない
- **`/easy_mode/export/{book_id}` に認証なし** → book_id をインクリメントするだけで他人の作品をダウンロード可能
- **(`/api/marketing/export_package/{book_id}` も認証なし** → 重大な情報漏洩リスク）

### 5.2 レート制限

[`easy_mode.py:12`](autonovel/src/backend/routers/easy_mode.py:12) で `generate_limiter` を import：
- `generate_content` には適用（[`easy_mode.py:233`](autonovel/src/backend/routers/easy_mode.py:233)）
- **`/easy_mode/export/{book_id}` にはレート制限なし**
- **`/api/marketing/export_package/{book_id}` にもレート制限なし**

### 5.3 SQL インジェクション

- SQLAlchemy ORM を使用しているので**基本的リスクは低い**
- ただし `BookRepository.get_by_id` 等の実装未確認

---

## 6. UX（ユーザー体験）上の問題

### 6.1 進捗の可視化

- `StatusReporter` クラスは存在するが、**UIへの SSE (Server-Sent Events) 接続が正常動作するか未確認**
- [`backend/routers/streaming.py`](autonovel/src/backend/routers/streaming.py) は `/easy_mode/generate/stream` を提供しているが、**POST版は廃止予定**（[`easy_mode.py:175-177`](autonovel/src/backend/routers/easy_mode.py:175)）

### 6.2 エラーメッセージの不親切さ

[`pipeline_steps.py:217`](autonovel/src/services/pipeline_steps.py:217)：
```python
reporter.report(
    f"🚨 本文執筆中にエラーが発生しました: {e}. プロットやキャラクター設定に問題がないか確認してください。",
    "error",
)
```

- **「API キーエラー」「レート制限」「タイムアウト」など具体的な原因が判別できない**
- ユーザーは「何が起きたか」がわからず、詰まる

### 6.3 キャンセル機能

[`easy_mode.py:358-376`](autonovel/src/backend/routers/easy_mode.py:358) の `/easy_mode/task/{task_id}`：
- `huey.revoke_by_id(task_id)` でタスク取り消し
- **しかし Huey の `revoke_by_id` は「実行中のタスク」をキャンセルする API ではなく「タスク投入を取り消す」 API**
- **執筆中の LLM 呼び出しを中断する仕組みはない** → ユーザーは停止ボタン押しても完了を待つしかない

### 6.4 結果確認

- **`/easy_mode/status/{task_id}` で完了確認**だが、`huey.result(task_id)` の結果は **メモリ内 or Redis 内**に保持
- デフォルト Huey バックエンドが SQLite（[`config.py:42`](autonovel/src/backend/config.py:42)）の場合、**ワーカープロセスが再起動すると結果が消える**
- **長時間の執筆後、サーバ再起動で結果消失** → 致命的 UX 問題

---

## 7. テストの妥当性

### 7.1 テストカバレッジ

[`pyproject.toml:62`](autonovel/pyproject.toml:62) で `--cov-fail-under=35`：
- **目標値が低すぎる**（業界標準は70-80%）
- [`tests/test_easy_mode_workflow.py`](autonovel/tests/test_easy_mode_workflow.py) は**モックのみ**で実フローを通していない
- **E2E テストが存在しない**（[`tests/integration/`](autonovel/tests/integration/) にはあるが、かんたんモード全体フローはカバーしていない）

### 7.2 テストデータの不整合

[`tests/test_easy_mode_workflow.py:124-148`](autonovel/tests/test_easy_mode_workflow.py)：
```python
await workflow.execute(
    mock_reporter,
    genre="ファンタジー",
    keywords=["test"],
    ...
)
```

- テストはモック LLM で通るが、**実際の LLM API を叩かないため品質保証にならない**
- **プロダクションで起きるエラーパス（LLM タイムアウト、レート制限、JSON パース失敗）がテストされていない**

---

## 8. 起動から1作品完成までの想定所要時間

### 8.1 ローカル初回セットアップ（30分〜数時間）
- 依存インストール（5分）
- DB マイグレーション（1分）
- LLM API キー取得・設定（5〜10分）
- フロントエンド `npm install`（5〜10分）
- 起動・デバッグ（10分〜1時間）

### 8.2 初回1作品作成（30分〜2時間）
- ジャンル・キーワード入力（1分）
- 企画推論（10秒）
- 8話執筆 × 2000字（30分〜1時間：LLM レートに依存）
- 監査・リライト（10分）
- マーケティング生成（10秒）
- ZIP ダウンロード（1秒）

**合計**: ローカル初回で **2時間以上**、Docker 利用でも **1時間** は覚悟が必要。

---

## 9. 総合評価

### 9.1 良い点

- **アーキテクチャの整理**: ワークフロー→ステップ→コンテキストの3層構造が綺麗
- **フォールバック設計**: LLM 障害時の degradation パスが複数層で存在
- **テストの量**: 単体テストは充実（少なくとも `tests/unit/` は1000ファイル以上）
- **設定の柔軟性**: 6つの LLM プロバイダ、環境変数による完全な上書き

### 9.2 致命的な問題（実運用ブロッカー）

1. **🔴 かんたんモードを起動する直接エンドポイントが存在しない可能性**（要確認）
2. **🔴 ZIP エクスポート時の book_id 認証なし**（情報漏洩）
3. **🔴 LLM API キー未設定時の挙動が不明確**（`mock` デフォルトで監査形骸化）
4. **🟠 Huey SQLite でサーバ再起動すると結果消失**
5. **🟠 GraphRAG デフォルト有効でローカル起動失敗**
6. **🟠 挿絵・EPUB・カバー画像が納品物に含まれない**（かんたんモードの名にそぐわない）
7. **🟡 マイグレーション自動実行の有無が不明**
8. **🟡 カタルシス分析・挿絵が無効化されている理由がコメントのみ**

### 9.3 中期的改善項目

- フロントエンドの API ベース URL 統一と環境切替
- `/easy_mode/export/{book_id}` への認証ミドルウェア追加
- レート制限の包括的適用
- E2E テストの追加（実 LLM or より現実に近いモック）
- エラーメッセージの詳細化（`API_KEY_MISSING` / `RATE_LIMIT_EXCEEDED` / `TIMEOUT` 等）
- 進捗の SSE 確実な接続確立
- タスク結果の永続化（Huey → PostgreSQL バックエンド）

---

## 10. 判定

### 「初回ユーザーが 30分以内に 1作品を納品まで完了できるか？」

### → **判定: NO** 🚫

#### 理由：
1. **環境構築に最低30分**（依存・DB・LLM API キー）
2. **初回作品生成に30分〜2時間**（LLM レート・トークン消費）
3. **途中で詰まる可能性が高い箇所が複数**（GraphRAG / mock プロバイダ / 認証 / 進捗可視化）
4. **「かんたん」とは言い切れない UI/UX 設計**（Huey タスク ID で状況確認、JSON 形式の結果等）

### 「エンジニアが既存環境を持っていれば動くか？」

### → **判定: たぶん YES**（80%）

ただし、以下の条件下：
- LLM API キーが正しく設定済み
- DB マイグレーション完了済み
- Redis or SQLite での Huey バックエンド動作確認済み
- フロントエンドとバックエンドの接続確認済み

---

## 11. 推奨アクション（即時）

| # | 優先度 | 項目 | 工数 |
|---|--------|------|------|
| 1 | P0 | かんたんモード起動エンドポイントを明示的に routers に追加 | 1h |
| 2 | P0 | `/easy_mode/export/{book_id}` に認証ミドルウェア追加 | 4h |
| 3 | P0 | LLM API キー未設定時の明示的な起動時バリデーション | 2h |
| 4 | P1 | `ENABLE_GRAPHRAG=False` をローカル起動時のデフォルトに | 0.5h |
| 5 | P1 | 納品 ZIP に EPUB/カバー画像を含める | 1d |
| 6 | P1 | E2E テスト 1本追加（モック LLM で全フロー） | 4h |
| 7 | P2 | Huey 結果の永続化 | 1d |
| 8 | P2 | エラーメッセージの構造化（error_code 付与） | 4h |

---

**結論**: コードベースは整理されているが、**初回ユーザーが体験する E2E フローは決して「スムーズ」とは言えない**。特に (1) かんたんモード起動エンドポイントの欠如、(2) 認証の欠如、(3) デフォルト設定での起動失敗の可能性は、商用化前に必ず対処すべき。
