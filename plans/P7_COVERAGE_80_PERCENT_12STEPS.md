# P7: テストカバレッジ80%突破 最終スプリント詳細実装計画書（全12ステップ）

**作成日**: 2026-09-15  
**対象**: AutoNovel v4.9.3（`e:/hhh`）  
**目標**: ユニットテストカバレッジ 65.84% (総合 61.68%) → **80.0% 以上**（CI ゲート突破）  
**実測ベースライン (2026-09-15 実測値)**:
- **カバレッジ率**: **65.84%** (covered 33,538 / 50,935 行, ブランチ 46.20%)
- **80.0% 到達に必要な追加カバー行**: **約 7,210 行**
- **既存ユニットテスト総数**: 2,800 passed (全約3,100テスト)
- **テスト方針**: 外部プロセス（Docker / Redis / ChromaDB / 外部API）への依存を排除し、完全自己完結型モックまたはインメモリ実装で高速・決定論的にパスするテストスイートを構築。

---

## 📊 現状と80%到達への定量分析

### 1. カバレッジ帯の分布 (全 691 ファイル)
- **80% 以上（達成済）**: 359 ファイル (52.0%)
- **50% 〜 79%（中間層）**: 171 ファイル (24.7%)
- **1% 〜 49%（低カバレッジ層）**: 146 ファイル (21.1%)
- **0%（未カバー）**: 14 ファイル (945 行)

### 2. カテゴリ別カバレッジ現況
| カテゴリ | カバレッジ率 | カバー行 / 全行 | 未カバー行 | 優先度 |
|---|---|---|---|:---:|
| `services` | 64.88% | 10,468 / 16,134 | 5,666 行 | ★★★ |
| `backend` | 56.49% | 7,649 / 13,540 | 5,891 行 | ★★★ |
| `easy_mode` | 53.02% | 948 / 1,788 | 840 行 | ★★★ |
| `infrastructure` | 55.93% | 971 / 1,736 | 765 行 | ★★ |
| `agents` | 73.20% | 5,850 / 7,992 | 2,142 行 | ★★ |
| `core` | 65.78% | 992 / 1,508 | 516 行 | ★★ |
| `models` | 79.80% | 2,026 / 2,539 | 513 行 | ★ |
| `domain` | 87.26% | 2,651 / 3,038 | 387 行 | 達成済 |

---

## 📋 全12ステップ 実装マトリクス

本計画は、未カバー行数が上位に集中しているボトルネックファイル（Top 20）を射程に収め、各ステップごとに独立したテストスイートを追加して **+7,250行以上** のカバーを達成します。

| Step | レイヤー / 対象モジュール | 作成テストファイル | 獲得予定カバー行 | 累計カバレッジ見込 |
|:---:|:---|:---|:---:|:---:|
| **Step 1** | `vector_store` クリーンアップ & パッケージ完全カバー | `tests/unit/services/test_vector_store_package_full.py` | +750 行 | 67.3% |
| **Step 2** | `age_client.py` (Apache AGE グラフDBクライアント) | `tests/unit/services/test_age_client_deep.py` | +400 行 | 68.1% |
| **Step 3** | `routers/branches.py` (IF分岐・差分・マージルーター) | `tests/unit/backend/test_routers_branches_deep.py` | +380 行 | 68.8% |
| **Step 4** | `easy_mode/phase3/asset_pack.py` (資産化パッケージ) | `tests/unit/easy_mode/test_asset_pack_deep.py` | +240 行 | 69.3% |
| **Step 5** | `easy_mode/phase3/ebook_export.py` (EPUB/PDF/MOBI) | `tests/unit/easy_mode/test_ebook_export_deep.py` | +230 行 | 69.8% |
| **Step 6** | `engine_context.py` & `backend/tasks/generation_tasks.py` | `tests/unit/backend/test_engine_and_generation_tasks.py` | +380 行 | 70.5% |
| **Step 7** | `agents/audit.py` & `agents/illustration_agent.py` | `tests/unit/agents/test_audit_and_illustration_deep.py` | +320 行 | 71.1% |
| **Step 8** | `services/rag_service.py` & `reflective_rag.py` | `tests/unit/services/test_rag_pipeline_deep.py` | +300 行 | 71.7% |
| **Step 9** | `publishers/narou.py` & `services/bible_service.py` | `tests/unit/services/test_publishers_and_bible_deep.py` | +320 行 | 72.3% |
| **Step 10** | `backend/multimedia_service.py` & `routers/patches.py` | `tests/unit/backend/test_multimedia_and_patches_deep.py` | +310 行 | 73.0% |
| **Step 11** | 残存 0%ファイル群（Cadence・Observability・Billing） | `tests/unit/test_zero_coverage_modules_bundle.py` | +300 行 | 73.6% |
| **Step 12** | 既存テスト失敗・エラー 314 件のモック修復 & 統合ゲート | `tests/conftest.py` および既存フィクスチャ補完 | +3,300 行 | **80.1%** ✅ |

---

## 🛠 各ステップ詳細実装仕様

### Step 1: `vector_store` キメラ解消 & 分割パッケージ網羅テスト
- **目的**: 旧 `src/services/vector_store.py` (625行) は `src/services/vector_store/` パッケージへ移行済みだが、同名ファイルとして残存し 0% の死蔵コードとして全体母数を引き下げている。本ステップで `pyproject.toml` omit に旧単体ファイルを登録（または整理）しつつ、新 `vector_store/` (`chroma.py`, `pgvector.py`, `in_memory.py`) の未カバー枝を完全網羅する。
- **対象ファイル**: `src/services/vector_store/__init__.py`, `chroma.py`, `pgvector.py`, `in_memory.py`
- **作成テストファイル**: `tests/unit/services/test_vector_store_package_full.py`
- **テスト内容**:
  1. `ChromaVectorStore`: コレクション自動作成、フィルタ付き検索、埋め込みベクトル次元エラー、BM25ハイブリッド検索のフォールバック。
  2. `PgVectorStore`: セッションエラー時のロールバック、コサイン距離クエリ構築、一括バッチインサート。
  3. `InMemoryFallbackStore`: メタデータ部分一致フィルタ、コサイン類似度ゼロ除算回避、リセット処理。
- **実装例**:
```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.services.vector_store import (
    ChromaVectorStore,
    PgVectorStore,
    InMemoryFallbackStore,
    get_default_store,
)

@pytest.mark.asyncio
async def test_in_memory_fallback_store_search_and_filter():
    store = InMemoryFallbackStore()
    await store.add_documents(
        collection_name="novel_test",
        ids=["doc1", "doc2"],
        documents=["魔王を倒した勇者", "日常の学園生活"],
        embeddings=[[1.0, 0.0], [0.0, 1.0]],
        metadatas=[{"genre": "fantasy"}, {"genre": "school"}],
    )
    res = await store.search("novel_test", query_embedding=[0.9, 0.1], limit=1)
    assert len(res) == 1
    assert res[0]["id"] == "doc1"
```
- **検証コマンド**: `pytest tests/unit/services/test_vector_store_package_full.py -v`

---

### Step 2: `age_client.py` (Apache AGE グラフDBクライアント) 深層テスト
- **目的**: 未カバー 489 行 (カバレッジ 18.4%) を抱える `src/services/age_client.py` に対し、PostgreSQL 拡張のエラーハンドリング、Cypher クエリ生成、SQLSTATE リトライロジックをテスト。
- **対象ファイル**: `src/services/age_client.py`
- **作成テストファイル**: `tests/unit/services/test_age_client_deep.py`
- **テスト内容**:
  1. `_RETRY_SQLSTATES` による指数バックオフリトライ（`40001` serialization_failure, `40P01` deadlock_detected, `57P03` 等）。
  2. `CypherResult` のイテレーション・サマリー展開・レコード抽出。
  3. パラメータ化クエリ (`$param`) のエスケープと agtype パース処理。
  4. NetworkX フォールバックモード（AGE 非活性時の自動切り替え）の検証。
- **検証コマンド**: `pytest tests/unit/services/test_age_client_deep.py -v`

---

### Step 3: `routers/branches.py` (IF分岐・Playthrough・Merge ルーター) テスト
- **目的**: 未カバー 433 行 (カバレッジ 22.5%) を持つ巨大ルーターの全エンドポイントを `TestClient` で検証。
- **対象ファイル**: `src/backend/routers/branches.py`
- **作成テストファイル**: `tests/unit/backend/test_routers_branches_deep.py`
- **テスト内容**:
  1. `/api/branches/fork`: 正常分岐作成、親エピソード不整合時の 404/422 エラー。
  2. `/api/branches/play/start`, `choose`, `end`: ゲームブック形式の選択肢遷移セッション管理。
  3. `/api/branches/merge`: コンフリクト発生時の差分レスポンス、コミット承認処理。
  4. WebSocket `/api/branches/ws`: 分岐プレビューのリアルタイム配信と切断処理。
- **検証コマンド**: `pytest tests/unit/backend/test_routers_branches_deep.py -v`

---

### Step 4: `easy_mode/phase3/asset_pack.py` (資産化パッケージ) 完全網羅
- **目的**: 未カバー 263 行 (カバレッジ 23.1%)。電子書籍・音声・イラスト・IFルートをまとめた ZIP 資産化ロジックをテスト。
- **対象ファイル**: `src/easy_mode/phase3/asset_pack.py`
- **作成テストファイル**: `tests/unit/easy_mode/test_asset_pack_deep.py`
- **テスト内容**:
  1. `AssetPackMetadata` のバリデーション、チェックサム計算（SHA-256）、マニフェスト生成。
  2. ZIP アーカイブ圧縮、解凍検証、ファイル欠損時のフォールバック処理。
  3. ライセンス情報 (`licensing`) の付与とメタデータ辞書化。
- **検証コマンド**: `pytest tests/unit/easy_mode/test_asset_pack_deep.py -v`

---

### Step 5: `easy_mode/phase3/ebook_export.py` (EPUB/PDF/MOBI) 出力テスト
- **目的**: 未カバー 257 行 (カバレッジ 23.7%)。出版用フォーマット生成器のテスト。
- **対象ファイル**: `src/easy_mode/phase3/ebook_export.py`
- **作成テストファイル**: `tests/unit/easy_mode/test_ebook_export_deep.py`
- **テスト内容**:
  1. `ebooklib` / `reportlab` 存在時と非存在時（`EPUB_AVAILABLE=False`）の graceful degradation テスト。
  2. 目次（TOC）生成、縦書き・横書き CSS レイアウト注入、ルビ記法変換。
  3. カバー画像バイナリ埋め込みと章別 XHTML 分割生成。
- **検証コマンド**: `pytest tests/unit/easy_mode/test_ebook_export_deep.py -v`

---

### Step 6: `engine_context.py` & `generation_tasks.py` 非同期タスクテスト
- **目的**: 未カバー計 438 行。執筆コンテキスト管理と Huey 非同期生成タスクの実行ライフサイクルをテスト。
- **対象ファイル**: `src/backend/engine_context.py`, `src/backend/tasks/generation_tasks.py`
- **作成テストファイル**: `tests/unit/backend/test_engine_and_generation_tasks.py`
- **テスト内容**:
  1. `EngineContext`: スレッドローカル/コンテキスト変数スコープ、トークンバジェット追跡、タイムアウト監視。
  2. `generation_tasks`: タスクキュー投入、進捗ステータス（PENDING → RUNNING → COMPLETED / FAILED）、失敗時リトライ。
- **検証コマンド**: `pytest tests/unit/backend/test_engine_and_generation_tasks.py -v`

---

### Step 7: `agents/audit.py` & `agents/illustration_agent.py` 監査・挿絵テスト
- **目的**: 未カバー計 367 行。原稿品質監査（テンション・矛盾・倫理）と挿絵プロンプト抽出エージェントをテスト。
- **対象ファイル**: `src/agents/audit.py`, `src/agents/illustration_agent.py`
- **作成テストファイル**: `tests/unit/agents/test_audit_and_illustration_deep.py`
- **テスト内容**:
  1. `AuditAgent`: ルビ・改行フォーマット違反、キャラ口調ブレ、NGワードの多角的検出とスコアリング。
  2. `IllustrationAgent`: シーン本文からのキャラ・情景・構図キーフレーズ抽出、SD/ComfyUI プロンプト整形。
- **検証コマンド**: `pytest tests/unit/agents/test_audit_and_illustration_deep.py -v`

---

### Step 8: `services/rag_service.py` & `reflective_rag.py` 検索・再考パイプライン
- **目的**: 未カバー計 333 行。小説特化 RAG のハイブリッド検索とリフレクション（自己反省・クエリ再構成）をテスト。
- **対象ファイル**: `src/services/rag_service.py`, `src/services/reflective_rag.py`
- **作成テストファイル**: `tests/unit/services/test_rag_pipeline_deep.py`
- **テスト内容**:
  1. `RAGService`: 伏線・設定用語のスコア付き近傍検索、チャンク結合、重複除外。
  2. `ReflectiveRAG`: 検索結果の関連性評価（Relevance Score）、不足時の自動クエリ書き換えループ。
- **検証コマンド**: `pytest tests/unit/services/test_rag_pipeline_deep.py -v`

---

### Step 9: `publishers/narou.py` & `services/bible_service.py` 出版・世界観管理
- **目的**: 未カバー計 389 行。なろう投稿自動化の通信モックおよびバイブル（キャラ辞書・年表・用語集）の同期検証。
- **対象ファイル**: `src/services/publishers/narou.py`, `src/services/bible_service.py`
- **作成テストファイル**: `tests/unit/services/test_publishers_and_bible_deep.py`
- **テスト内容**:
  1. `NarouPublisher`: ログインセッション維持、HTMLスクレイピングによるCSRFトークン抽出、話数追加・更新リクエスト。
  2. `BibleService`: キャラクター相関図のJSON更新、設定矛盾の自動フラグ付け、プロット連携。
- **検証コマンド**: `pytest tests/unit/services/test_publishers_and_bible_deep.py -v`

---

### Step 10: `multimedia_service.py` & `routers/patches.py` パッチ・配信テスト
- **目的**: 未カバー計 349 行。マルチメディアアセット生成管理と差分パッチ適用ルーターを検証。
- **対象ファイル**: `src/backend/multimedia_service.py`, `src/backend/routers/patches.py`
- **作成テストファイル**: `tests/unit/backend/test_multimedia_and_patches_deep.py`
- **テスト内容**:
  1. `MultimediaService`: BGM/効果音/挿絵のジョブ並列ディスパッチとファイルリンク解決。
  2. `routers/patches`: JSON Patch 適用による部分更新、コンフリクト検出、3-way マージ。
- **検証コマンド**: `pytest tests/unit/backend/test_multimedia_and_patches_deep.py -v`

---

### Step 11: ゼロカバレッジ残存モジュール群の統合網羅
- **目的**: 0% のまま放置されている小規模モジュール群（計 14 ファイル、320 行）を一挙に 100% 化し、全体の「0%ファイル」を完全にゼロにする。
- **対象ファイル**:
  - `src/services/cadence/compound_merger.py` (69行)
  - `src/services/cadence/span_extractor.py` (59行)
  - `src/backend/observability.py` (50行)
  - `src/models/billing.py` (24行)
  - `src/services/illustration/prompt_builder.py` (21行)
  - `src/services/cadence/models.py` (20行)
  - `src/services/ncs_calibration.py` (19行)
  - `src/models/context.py` (15行)
  - `src/services/data_loader.py` (15行)
  - `src/services/narrative_scoring_service.py` (14行)
  - `src/shared/event_bus.py`, `src/shared/network.py`, `src/core/exceptions.py`
- **作成テストファイル**: `tests/unit/test_zero_coverage_modules_bundle.py`
- **検証コマンド**: `pytest tests/unit/test_zero_coverage_modules_bundle.py -v`

---

### Step 12: 既存失敗・エラー（314件）のモック修復 & CI 80% ゲート有効化
- **目的**: 現在実測で発生している 242 件の Failed および 72 件の Error は、主として「実PostgreSQL / Docker / Redis / ChromaDB が起動していない環境での接続試行」や「未定義モックの呼び出し」によるもの。これらを SQLite インメモリまたは AsyncMock へ置換修復することで、本来通過すべき既存テストを復帰させ、一気に **+3,300行** 以上のカバー行を有効化する。
- **対象ファイル**: `tests/conftest.py`, `tests/integration/conftest.py`
- **作業内容**:
  1. `tests/conftest.py` に `mock_docker_and_services` オートユーズフィクスチャを導入し、外部コンテナ未起動時でもテストがエラー終了しないようガード。
  2. `tests/unit/publishers/test_narou.py` や `tests/branches/test_e2e_*.py` の SQLAlchemy セッションフィクスチャをインメモリ SQLite 互換に統一。
  3. `pyproject.toml` の `--cov-fail-under` を `35` → `80` に引き上げ、CI ゲートを更新。
- **検証コマンド**: `pytest --cov=src --cov-fail-under=80`

---

## 🎯 期待成果物と完了基準

1. **成果物**:
   - `tests/unit/` 配下の新規テストファイル 11 本
   - 既存フィクスチャ整備によるテスト失敗 0 件化（Pass 率 100%）
   - 最新 `coverage.json` スナップショット
2. **受け入れ基準（Definition of Done）**:
   - [ ] `pytest tests/unit` が **All Green（0 failed, 0 error）** でパスすること
   - [ ] 全体ステートメントカバレッジが **80.0% 以上** に達すること
   - [ ] 0% カバレッジのファイルが **0 件** になること
   - [ ] `pyproject.toml` の CI カバレッジ閾値が 80% で設定されていること
