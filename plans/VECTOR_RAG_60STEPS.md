# VectorStore + RAG 検索サービス 実装計画 (1〜60 ステップ)

対象リポジトリ: `autonovel`
対象モジュール:
- `src/services/vector_store.py` (ChromaDB + BM25, 655 行)
- `src/services/rag_service.py` (GraphRAG + コサインバリフォールバック, 198 行)
- `src/services/embedding_service.py` (OpenAI / 疑似埋め込み, 67 行)
- `src/infrastructure/database/models/chunk.py` (pgvector `ChapterChunk`)
- `alembic/versions/00000000_initial_migration.py` (プレースホルダ)
- `requirements.txt` (chromadb 1.5.9, rank-bm25 0.2.2, pgvector 0.5.0 は定義済)

この計画は「低性能な LLM でも実装できる粒度」に分解している。
各ステップは 1 PR ≒ 1 コミットに収まるサイズで、コンパイル・テスト可能な状態を維持する。

---

## 0. 全体方針 (必読)

1. **後方互換を保ったまま段階的に強化する。** 既存 API シグネチャは壊さない。
2. **ハード依存化は Settings フラグで段階導入する。** 一気に `requirements.txt` を締めると CI が壊れるため、`REQUIRE_CHROMA` / `REQUIRE_PG` を `False` から `True` に段階移行する。
3. **テストを先に書く (TDD-lite)。** 各ステップに対応する単体テストを先に追加 → 実装。
4. **1 ステップ = 1 機能 / 1 ファイル内変更** を基本とする。複数ファイルに渡る場合は更に分割する。
5. **`HAS_CHROMA` フォールバックは当面残す。** `REQUIRE_CHROMA=False` のときは `BaseVectorStore` の `InMemoryFallbackStore` で代替。
6. **Alembic マイグレーションは 1 機能 1 リビジョン** とし、ダウングレードも必ず書く。
7. **pgvector 必須化は段階移行**:
   - Step 1-10: 既存挙動を維持
   - Step 11-30: `REQUIRE_PG=False` で警告のみ
   - Step 31-45: `REQUIRE_PG=True` を Opt-in
   - Step 46-60: ドキュメント・サンプル・最終クリーンアップ

---

## Phase A: テストインフラ・可用性フラグ整備 (Step 1-10)

### Step 1: テスト用 conftest に pgvector 可用性フラグ追加

**ファイル**: `tests/conftest.py`
**変更内容**:
- 既存の `CHROMADB_AVAILABLE` / `RANK_BM25_AVAILABLE` フラグ定義の直後に `PGVECTOR_AVAILABLE` フラグを追加。
- フラグは try-import ベース (pgvector パッケージ存在チェック) で、CI ではモック切替できるよう `os.environ.get("AUTONOVEL_FORCE_PGVECTOR", "1") == "1"` で上書き可能に。
**検証**: `pytest tests/conftest.py -k "test_availability" --collect-only` で新規フラグが認識されること。
**LLM 指示**: try/except ブロックを 1 つコピペし、変数名だけ変更。所要 5 分。

### Step 2: embedding_service の batch インターフェース設計 (テスト先行)

**ファイル新規**: `tests/unit/test_embedding_service_batch.py`
**追加内容**:
- `TestEmbeddingServiceBatch` クラス。
- `test_get_embeddings_batch_empty` (空リスト → 空リスト)
- `test_get_embeddings_batch_single` (要素 1 → 長さ 1)
- `test_get_embeddings_batch_preserves_order` (順序保持)
- `test_get_embeddings_batch_respects_batch_size` (内部 `_BATCH_SIZE` 分割をモックで検証)
**注意**: まだ実装は追加しない。`pytest -k "TestEmbeddingServiceBatch"` は Red になる。

### Step 3: embedding_service へ `get_embeddings_batch` スタブ実装 (Green)

**ファイル**: `src/services/embedding_service.py`
**追加内容**:
- クラス定数 `_BATCH_SIZE: int = 64` を追加。
- `get_embeddings_batch(self, texts: list[str], batch_size: int | None = None) -> list[list[float]]` メソッドを追加。
- 内部実装は **`get_embedding` を順次呼び出すだけ** (本物のバッチ API は Step 23 で実装)。
- 空入力 / 空白入力は `[0.0] * 1536` を返すよう既存仕様を踏襲。
**検証**: `pytest tests/unit/test_embedding_service_batch.py -v` で Green になる。

### Step 4: embedding_service の `get_embedding` を batch 経由に切替

**ファイル**: `src/services/embedding_service.py`
**変更内容**:
- 既存の `get_embedding(self, text: str)` を `get_embeddings_batch([text])[0]` のシン・ラッパに置換 (API は不変)。
- 内部ロジックを `_call_openai_embeddings(texts: list[str])` に切り出し、`get_embedding` と `get_embeddings_batch` の両方から呼ぶ。
**検証**: 既存テスト `tests/unit/test_vector_store.py` などが全件 Green であること。

### Step 5: pgvector 利用可否のシングルトン化

**ファイル**: `src/infrastructure/database/models/chunk.py`
**変更内容**:
- 既存の `HAS_PGVECTOR` モジュール変数を `_detect_pgvector()` 関数で算出する形に変更。
- `_detect_pgvector()` は `importlib.util.find_spec("pgvector")` を使い、`ImportError` に依存しない。
- 公開 API (`HAS_PGVECTOR`) は維持。
**検証**: `python -c "from src.infrastructure.database.models.chunk import HAS_PGVECTOR; print(HAS_PGVECTOR)"` で期待値。

### Step 6: Settings に `REQUIRE_PG` / `REQUIRE_CHROMA` フラグ追加

**ファイル**: `src/backend/config.py`
**追加内容**:
```python
REQUIRE_PG: bool = False           # pgvector 必須化 (Opt-in)
REQUIRE_CHROMA: bool = False       # chromadb 必須化 (Opt-in)
RAG_FALLBACK_MODE: Literal["memory", "error"] = "memory"  # 不在時の挙動
RAG_BATCH_SIZE: int = 64
RERANKER_BACKEND: Literal["none", "simple", "cross_encoder"] = "none"
RERANKER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
```
**検証**: `from src.backend.config import settings; print(settings.REQUIRE_PG)` が `False` を返す。

### Step 7: Settings の `.env.example` 反映

**ファイル**: `.env.example`
**追加**: Step 6 と同名のキーをコメント行付きで列挙。
**検証**: フォーマット確認 (`grep` レベル)。

### Step 8: `InMemoryFallbackStore` のスケルトン追加 (テスト先行)

**ファイル**: `tests/unit/test_in_memory_fallback_store.py` (新規)
**追加内容**:
- `InMemoryFallbackStore` の API 契約テスト: `add_documents`, `search`, `delete_by_id`, `clear_collection` のシグネチャ確認。
- 現状は実装がないため ImportError になる → テストは Skip で OK (`pytest.mark.skipif(not HAS_INMEM, reason="wip")`)。

### Step 9: `InMemoryFallbackStore` 実装

**ファイル**: `src/services/vector_store.py`
**追加内容**:
- `class InMemoryFallbackStore(BaseVectorStore)` を新規追加。
- 内部: `dict[collection_name, list[(id, doc, emb, meta)]]`。
- `search` は brute-force コサイン。
- `add_documents` は append、`delete_by_id` は filter。
- `clear_collection` はキー削除。
- エクスポート: `__all__` に追加。
**検証**: Step 8 のテストを Skip 解除 → Green になる。

### Step 10: `InMemoryFallbackStore` の LRU キャッシュ (件数上限)

**ファイル**: `src/services/vector_store.py`
**変更内容**:
- `InMemoryFallbackStore.__init__` に `max_items_per_collection: int = 10000` 引数追加。
- `add_documents` 内で長さが超過したら古いものから削除 (FIFO で十分)。
**検証**: Step 8 テストに `test_add_documents_respects_max_items` を追加 → Green。

---

## Phase B: 設定と依存関係の整備 (Step 11-20)

### Step 11: 環境変数 `AUTONOVEL_RAG_MODE` のパース追加

**ファイル**: `src/services/vector_store.py`
**追加内容**:
- モジュールロード時に `os.environ.get("AUTONOVEL_RAG_MODE", "auto")` を読んで `_RAG_MODE` を確定 (auto / chroma / memory)。
- `get_default_store()` ファクトリ関数を追加: `auto` のとき `HAS_CHROMA` を見て切替、`chroma` のとき `ChromaVectorStore`、`memory` のとき `InMemoryFallbackStore`。
**検証**: `tests/unit/test_vector_store.py::TestStoreFactory` を新規追加 (パラメタライズ) → Green。

### Step 12: `ChromaClientProvider` のパス設定の環境変数化

**ファイル**: `src/services/vector_store.py`
**変更内容**:
- `__init__` で `db_path` が未指定なら `settings.CHROMA_DB_PATH or "./chroma_db"` を使う。
**注**: `settings.CHROMA_DB_PATH` は次のステップで追加。

### Step 13: Settings に `CHROMA_DB_PATH` 追加

**ファイル**: `src/backend/config.py`
**追加**:
```python
CHROMA_DB_PATH: str = Field(default_factory=lambda: str(STORAGE_DIR / "chroma_db"))
```
**検証**: `print(settings.CHROMA_DB_PATH)` で `storage/chroma_db` が出る。

### Step 14: `requirements.txt` の `chromadb` / `rank-bm25` ハード化準備

**ファイル**: `requirements.txt`
**変更内容**:
- `chromadb==1.5.9` の行を `chromadb>=1.5.0,<2.0.0` に置換 (CI の互換性バッファ)。
- `rank-bm25==0.2.2` の行を `rank-bm25>=0.2.2` に置換。
- セクションコメント `# --- Vector / RAG (Hard deps) ---` を追加。
**検証**: `pip install -r requirements.txt --dry-run` が通る。

### Step 15: `pyproject.toml` への RAG 依存宣言

**ファイル**: `pyproject.toml`
**追加内容**:
- `[project.optional-dependencies] rag` セクションを新設し、Step 14 と同じ依存を列挙 (optional として残す)。
- これにより `pip install autonovel[rag]` で RAG フルセットが入る。
**検証**: `pip install -e ".[rag]"` が成功。

### Step 16: `Dockerfile` への chromadb 用ビルド依存追加 (任意)

**ファイル**: `Dockerfile`
**追加内容**:
- `RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*` を Python インストール前に追加 (chromadb の C 拡張対策)。
- 不要ならこのステップは Skip 可能。
**注**: CI が軽いイメージで回っている場合のみ実施。判断は次フェーズ。

### Step 17: docker-compose に `chroma` サービス追加 (オプション)

**ファイル**: `docker-compose.yml`
**追加内容**:
- `chroma:` サービス (image: `chromadb/chroma:latest`, port 8000, volume `chroma_data`) を追加。
- `autonovel:` サービスから `CHROMA_HOST=chroma` / `CHROMA_PORT=8000` 環境変数を設定。
**注**: Standalone モード (`ChromaClientProvider`) を使う場合、本ステップは不要。後述の Step 41 で `ChromaHttpStore` を追加する際に必要。

### Step 18: `vector_store` パッケージ・レベル `__all__` 明示

**ファイル**: `src/services/vector_store.py`
**変更内容**:
- ファイル末尾に `__all__ = [...]` を追加 (Step 9 で追加し忘れ対策)。
- 並び順はアルファベット推奨。

### Step 19: 既存テストの import パス統一

**ファイル**: `tests/unit/test_vector_store.py`
**変更内容**:
- `from src.services.vector_store import (...)` の行に Step 9, 18 で追加した `InMemoryFallbackStore` / `get_default_store` を追記。
- 不要な `pytest.importorskip` の置換。
**検証**: `pytest tests/unit/test_vector_store.py` が Green。

### Step 20: conftest のフィクスチャに `tmp_chroma_path` 追加

**ファイル**: `tests/conftest.py`
**追加内容**:
```python
@pytest.fixture
def tmp_chroma_path(tmp_path):
    p = tmp_path / "chroma"
    p.mkdir()
    return str(p)
```
**検証**: `pytest --fixtures tests/` で `tmp_chroma_path` が表示される。

---

## Phase C: EmbeddingService 強化 (Step 21-30)

### Step 21: `EmbeddingService` にキャッシュ層 (LRU) 追加

**ファイル**: `src/services/embedding_service.py`
**追加内容**:
- `functools.lru_cache(maxsize=2048)` を `_hash_key(text)` ベースで適用。
- ヒット率は統計用カウンタ `self._cache_hits`, `self._cache_misses` でカウント。
- `cache_info()` メソッドで公開。
**検証**: 同一テキストを 2 回呼ぶと `_cache_hits` が増えることをテスト。

### Step 22: 埋め込みリクエストのレート制御

**ファイル**: `src/services/embedding_service.py`
**追加内容**:
- `time.sleep(0.01)` ベースのトークンバケット (RPM 60 想定) を `_rate_limit_wait()` として導入。
- テストでは `monkeypatch` で `time.sleep` をモック。
**検証**: 連続 5 回呼出しで sleep が 4 回以上発火することを確認。

### Step 23: OpenAI バッチ API への切替

**ファイル**: `src/services/embedding_service.py`
**変更内容**:
- `_call_openai_embeddings(texts: list[str])` で `client.embeddings.create(input=texts, model=...)` を呼ぶ (OpenAI は input リストを受け付ける)。
- 失敗時は `_BATCH_SIZE` ごとに分割リトライ。
- レスポンスの `index` で順序を保証。
**検証**: 既存 `test_embedding_service_batch.py` の `test_get_embeddings_batch_preserves_order` が API レベルでも Green になること (モックで OK)。

### Step 24: `get_embeddings_batch` のセマンティクス明文化

**ファイル**: `src/services/embedding_service.py`
**追加内容**:
- docstring に「空文字列 / 空白のみの入力は 1536 次元のゼロベクトルを返す」と明記。
- `tests/unit/test_embedding_service_batch.py::test_get_embeddings_batch_blank_inputs` を追加。
**検証**: 上記テストが Green。

### Step 25: `EmbeddingService` の `__repr__` 追加

**ファイル**: `src/services/embedding_service.py`
**追加内容**:
- `__repr__` で `model_name`, `cache_hits`, `cache_misses` を表示。
- デバッグ用。シークレットは含めない。
**検証**: `repr(embedding_service)` が例外を出さない。

### Step 26: 埋め込みキャッシュを Redis に切替可能に (インターフェース)

**ファイル**: `src/services/embedding_service.py`
**追加内容**:
- 抽象基底 `EmbeddingCache` (抽象メソッド `get(key)`, `set(key, vec)`, `info()`)。
- 具象 `LRUEmbeddingCache` (既存 lru_cache ベース) と `RedisEmbeddingCache` スタブ (TODO ステップで実装) を追加。
- `EmbeddingService.__init__` に `cache: EmbeddingCache | None = None` 引数追加。
**検証**: テストで `EmbeddingService(cache=LRUEmbeddingCache())` が動くこと。

### Step 27: `RedisEmbeddingCache` スタブ実装

**ファイル**: `src/services/embedding_service.py`
**追加内容**:
- `RedisEmbeddingCache` で `src.services.redis_cache` のクライアントを import。
- 接続失敗時は `LRUEmbeddingCache` に自動フォールバックし、warning ログ。
**検証**: モックで Redis 例外 → LRU に切替わることをテスト。

### Step 28: `EmbeddingService.embed_texts` 公開 API 化

**ファイル**: `src/services/embedding_service.py`
**追加内容**:
- `get_embeddings_batch` のエイリアスとして `embed_texts` を公開 (対称性の為)。
- `__all__` 更新。
**検証**: `from src.services.embedding_service import embed_texts` で import 可能。

### Step 29: バッチサイズ動的設定

**ファイル**: `src/services/embedding_service.py`
**変更内容**:
- `get_embeddings_batch` の `batch_size` 引数を尊重しつつ、デフォルトを `settings.RAG_BATCH_SIZE` から取る。
**検証**: テストで `monkeypatch.setattr(settings, "RAG_BATCH_SIZE", 8)` 後、分割回数が変化することを確認。

### Step 30: EmbeddingService の統合テスト 1 件追加

**ファイル**: `tests/integration/test_embedding_pipeline.py` (新規)
**追加内容**:
- ダミー OpenAI クライアントで 100 テキストを一括 encode → 順序保持・次元一致を確認。
- 実 API キーはモックで潰す。
**検証**: `pytest tests/integration/test_embedding_pipeline.py -v`。

---

## Phase D: VectorStore 性能改善 (Step 31-40)

### Step 31: `ChromaVectorStore.add_documents` のチャンク化

**ファイル**: `src/services/vector_store.py`
**変更内容**:
- `add_documents` で `ids` の長さが 416 を超えたら分割 (ChromaDB のバッチ上限)。
- 分割は `for chunk in chunks_of(items, 416)`。
**検証**: 1000 ドキュメントを add → 例外なく完了することをテスト。

### Step 32: `ChromaVectorStore.search` の `include` を明示

**ファイル**: `src/services/vector_store.py`
**変更内容**:
- `search` 内で `include=["documents", "metadatas", "distances", "embeddings"]` を要求 (呼び出し側が必要分のみ使えるよう、戻り値は従来通り id/content/metadata/distance)。
- `embeddings` が必要なケース (再ランク) 向けに `search_with_embeddings()` を別メソッドに分離。
**検証**: 既存テストが Green であること (戻り値互換)。

### Step 33: `get_collection_stats` の `peek` フォールバック

**ファイル**: `src/services/vector_store.py`
**変更内容**:
- 古い Chroma バージョンで `count()` が失敗する環境向け、`peek(limit=1)` で存在だけ確認するフォールバック追加。
- 例外時は `{"count": -1, "error": str(e)}` を返却。
**検証**: テストで `collection.count` を `side_effect=Exception` にモンキーパッチ → 期待値。

### Step 34: `hybrid_search` のパラメータ化テスト追加

**ファイル**: `tests/unit/test_vector_store.py`
**追加内容**:
- alpha ∈ {0.0, 0.5, 1.0} × top_k ∈ {1, 5, 20} の組み合わせ 9 ケース。
- BM25 とベクトル検索をモックでスタブ。
**検証**: 9 ケースすべて Green。

### Step 35: `hybrid_search` のフォールバック追加

**ファイル**: `src/services/vector_store.py`
**変更内容**:
- BM25 インデックス未構築時はベクトル検索のみを返す (`HAS_BM25=False` への耐性)。
- alpha 異常値 (負 / 1 超) は clamp して warning ログ。
**検証**: 既存テストの不変 + 新規 `test_hybrid_search_without_bm25_index`。

### Step 36: `InMemoryFallbackStore.hybrid_search` 実装

**ファイル**: `src/services/vector_store.py`
**変更内容**:
- `InMemoryFallbackStore` に簡易 hybrid_search (ベクトルのみ) を追加。
- BM25 は `rank_bm25` 不在環境では空文字列を返す。
**検証**: テストで `InMemoryFallbackStore` 経由の hybrid_search が動作。

### Step 37: `ChromaVectorStore` の `rebuild_bm25_index` を async 化

**ファイル**: `src/services/vector_store.py`
**変更内容**:
- `rebuild_bm25_index` の現行実装は同期関数で `collection.get()` を呼ぶ。
- `async def rebuild_bm25_index_async` を新設し、内部で `asyncio.to_thread` を使用。
- 既存メソッドはラッパとして残す (後方互換)。
**検証**: `await store.rebuild_bm25_index_async("episodic")` がエラーなく完了。

### Step 38: `CollectionType` のカバレッジ監査ヘルパ追加

**ファイル**: `src/services/vector_store.py`
**追加内容**:
- 関数 `audit_collection_coverage() -> dict[str, list[str]]` を追加。
- 各 CollectionType について `_ensure_collection` を呼び、成否を返す。
- CI 用の `scripts/audit_vector_coverage.py` (新規) から呼び出す。
**検証**: テストで `audit_collection_coverage()` が 6 種すべてを返すこと。

### Step 39: `audit_vector_coverage.py` スクリプト

**ファイル**: `scripts/audit_vector_coverage.py` (新規)
**追加内容**:
- `from src.services.vector_store import audit_collection_coverage` を呼ぶ CLI。
- 終了コード: 0 = 全成功、1 = 失敗あり。
**検証**: `python scripts/audit_vector_coverage.py` が exit 0。

### Step 40: `VectorStoreProtocol` (Protocol 型) 追加

**ファイル**: `src/services/vector_store.py`
**追加内容**:
- `from typing import Protocol` で `VectorStoreProtocol` を定義。
- 既存 `BaseVectorStore(ABC)` との併存。Protocol 側はダックタイピング用。
- `__all__` に追加。
**注**: 既存 ABC を置換しない。段階的移行のため。

---

## Phase E: pgvector 必須化 (Step 41-50)

### Step 41: `ChromaHttpStore` 追加 (スタンドアロン / HTTP)

**ファイル**: `src/services/vector_store.py`
**追加内容**:
- `ChromaHttpStore(BaseVectorStore)` クラス。
- `ChromaClientProvider` に `host` / `port` 引数を追加し、`chromadb.HttpClient` を使う分岐を実装。
- 環境変数 `CHROMA_HOST` / `CHROMA_PORT` を読む。
**検証**: モックで `chromadb.HttpClient` の `get_or_create_collection` を検証。

### Step 42: pgvector インデックス用 Alembic マイグレーション雛形

**ファイル**: `alembic/versions/0003_pgvector_chapter_chunks.py` (新規)
**追加内容**:
- `upgrade()`:
  - `CREATE EXTENSION IF NOT EXISTS vector;`
  - `ALTER TABLE chapter_chunks ALTER COLUMN embedding TYPE vector(1536);` (SQLite では no-op)
  - `CREATE INDEX IF NOT EXISTS ix_chapter_chunks_embedding ON chapter_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);`
- `downgrade()`:
  - `DROP INDEX IF EXISTS ix_chapter_chunks_embedding;`
**検証**: `alembic upgrade head --sql` で生成 SQL をレビュー。

### Step 43: マイグレーションの SQLite 互換化

**ファイル**: `alembic/versions/0003_pgvector_chapter_chunks.py`
**変更内容**:
- 既存の `00000000_initial_migration.py` はプレースホルダだが、本マイグレーションから `chapter_chunks` テーブルが暗黙に必要。
- `op.execute("SELECT 1")` で `op.get_bind().dialect.name == "postgresql"` を確認し、Postgres のみ実行する分岐を追加。
**検証**: `DATABASE_URL=sqlite:///./autonovel.db alembic upgrade head` が成功。

### Step 44: `ChapterChunk` の `__table_args__` にインデックス追加

**ファイル**: `src/infrastructure/database/models/chunk.py`
**変更内容**:
- `__table_args__ = (Index("ix_chapter_chunks_chapter_id_chunk_index", "chapter_id", "chunk_index"),)` を追加。
- pgvector インデックスは Alembic 側で管理 (Step 42)。
**検証**: 既存テストが Green。

### Step 45: `RagService.search_similar_chunks` を pgvector 専用化

**ファイル**: `src/services/rag_service.py`
**変更内容**:
- 旧 SQLite フォールバック (`else` 節) を **削除**。
- `HAS_PGVECTOR` が `False` かつ `settings.REQUIRE_PG` が `True` の場合は `RuntimeError` を送出。
- `REQUIRE_PG=False` のときは `InMemoryFallbackStore` を経由する。
**検証**: 既存 `tests/unit/test_rag_service.py` のテストを更新 (sqlite フォールバック依存を削除) → Green。

### Step 46: `REQUIRE_PG=True` 環境での起動時バリデーション

**ファイル**: `src/backend/config.py` または `src/core/container/app.py`
**変更内容**:
- 起動時に `settings.REQUIRE_PG and not HAS_PGVECTOR` の組合せを検出し、`RuntimeError` で fail-fast。
- ログメッセージ: "pgvector is required but not installed. Run: pip install pgvector==0.5.0"
**検証**: 環境変数を切替えて手動 smoke。

### Step 47: `RagService` の `query_embedding` バッチ化

**ファイル**: `src/services/rag_service.py`
**変更内容**:
- `search_similar_chunks` でクエリ単発ではなく `embedding_service.get_embeddings_batch` を呼ぶよう変更。
- ただし 1 クエリなのでオーバーヘッドはほぼ無いが、API の整合性のため。
**検証**: 既存テストが Green。

### Step 48: `RagService.build_rag_context` のメトリクス追加

**ファイル**: `src/services/rag_service.py`
**追加内容**:
- `_last_call_stats: dict[str, Any]` 属性。
- `search_similar_chunks` でヒット数 / レイテンシを記録。
- `get_last_stats()` で公開。
**検証**: テストで stats が dict で返ること。

### Step 49: チャンク埋め込み upsert のバッチヘルパ

**ファイル**: `src/services/vector_store.py` (または新規 `src/services/chunk_ingestion.py`)
**追加内容**:
- `async def upsert_chunks(store: BaseVectorStore, chunks: list[ChapterChunk], collection: str, batch_size: int = 64) -> int`。
- 各チャンクの `embedding` を `embedding_service.embed_texts([c.content for c in chunks])` で取得。
- 戻り値は登録件数。
**検証**: ダミー 10 チャンクで正常完了。

### Step 50: `RagService.retrieve_for_episode` 公開 API

**ファイル**: `src/services/rag_service.py`
**追加内容**:
- `def retrieve_for_episode(self, session, *, book_id, episode_number, character_name, top_k=3) -> dict[str, str]`
- `{"graph": str, "vector": str, "stats": dict}` を返す薄いラッパ。
- `build_rag_context` を内部で呼ぶ。
**検証**: 既存テストが Green + 新規テスト 1 件。

---

## Phase F: Cross-Encoder Reranking 導入 (Step 51-58)

### Step 51: Reranker プロトコル定義

**ファイル**: `src/services/reranker.py` (新規)
**追加内容**:
```python
class Reranker(Protocol):
    async def rerank(self, query: str, docs: list[str], top_k: int) -> list[tuple[int, float]]: ...
```
- `__all__ = ["Reranker", "NoopReranker", "SimpleReranker", "CrossEncoderReranker"]`
**検証**: `from src.services.reranker import NoopReranker` で import 可能。

### Step 52: `NoopReranker` 実装

**ファイル**: `src/services/reranker.py`
**追加内容**:
- 入力順そのまま + スコア 0.0 を返す。
**検証**: テストで `await NoopReranker().rerank("q", ["a","b","c"], 2)` → `[(0,0.0),(1,0.0)]`。

### Step 53: `SimpleReranker` 実装 (コサイン類似度ベース)

**ファイル**: `src/services/reranker.py`
**追加内容**:
- 内部で `embedding_service.get_embedding` をクエリ / 各 doc に適用。
- 類似度降順で top_k 返却。
- `settings.RERANKER_BACKEND == "simple"` で自動切替。
**検証**: テストで順序が期待通り。

### Step 54: `CrossEncoderReranker` スタブ (sentence-transformers 条件付き)

**ファイル**: `src/services/reranker.py`
**追加内容**:
- `try: from sentence_transformers import CrossEncoder; HAS_CE = True; except Exception: HAS_CE = False`。
- モデル名は `settings.RERANKER_MODEL` (デフォルト `cross-encoder/ms-marco-MiniLM-L-6-v2`)。
- `HAS_CE=False` 時は `RuntimeError` を送出 (`settings.RERANKER_BACKEND == "cross_encoder"` のときのみ fail-fast)。
**検証**: 環境変数 `RERANKER_BACKEND=cross_encoder` + `HAS_CE=False` で例外。

### Step 55: `RagService.rerank` 公開

**ファイル**: `src/services/rag_service.py`
**追加内容**:
- `def get_reranker(self) -> Reranker` (シングルトン生成)。
- `async def rerank(self, query: str, docs: list[str], top_k: int) -> list[tuple[int, float]]`。
**検証**: `NoopReranker` がデフォルトで返ること。

### Step 56: `build_rag_context` で reranker を組み込む

**ファイル**: `src/services/rag_service.py`
**変更内容**:
- ハイブリッド検索結果 (`similar_chunks`) を rerank で並び替え。
- `RERANKER_BACKEND=none` のときは元の順序を保持。
**検証**: 既存テストに `test_build_rag_context_respects_reranker_backend` を追加。

### Step 57: reranker 設定の `__init__` 引数化

**ファイル**: `src/services/rag_service.py`
**変更内容**:
- `GraphRAGService.__init__` に `reranker: Reranker | None = None` を追加。
- グローバル `rag_service` インスタンスはデフォルト `None` (= lazy)。
**検証**: テストで reranker を差し替え可能。

### Step 58: `requirements.txt` への `sentence-transformers` 条件付き追加

**ファイル**: `requirements.txt`
**追加**:
- `# sentence-transformers>=2.6.0; python_version >= "3.10"  # for RERANKER_BACKEND=cross_encoder` (コメントアウト)。
- 別ファイル `requirements-rag.txt` を新規作成し、こちらに分離しても良い。
**検証**: フォーマット確認。

---

## Phase G: 性能計測・最終クリーンアップ (Step 59-60)

### Step 59: 100 チャンク規模のパフォーマンステスト追加

**ファイル**: `tests/perf/test_vector_store_perf.py` (新規, `tests/perf/__init__.py` も)
**追加内容**:
- 100 チャンク × 1536 次元で `add_documents` ＋ `search` の合計時間測定。
- 閾値: add < 2.0s, search < 0.5s (CI では緩め)。
- `pytest -m perf` でマーキング。
- 失敗時は `pytest.skip` で OK (性能閾値はハードにしない)。
**検証**: `pytest -m perf tests/perf/test_vector_store_perf.py -v` で通過。

### Step 60: ドキュメント・README 更新

**ファイル**: `README.md` (RAG セクション) + `docs/rag_setup.md` (新規)
**追加内容**:
- `RERANKER_BACKEND` / `REQUIRE_PG` / `REQUIRE_CHROMA` の説明。
- `pip install -e ".[rag]"` の実行手順。
- `alembic upgrade head` の必要性。
- 100 チャンク規模のベンチ結果 (Step 59 由来) をテーブルで記載。
- トラブルシューティング: `HAS_CHROMA=False` の診断手順。
**検証**: `grep -E "REQUIRE_(PG|CHROMA)|RERANKER_BACKEND" README.md docs/rag_setup.md` でヒット確認。

---

## 3. 実装の進め方 (チェックリスト)

各ステップの実装時に以下を必ず確認:

- [ ] 対象ファイルは Read ツールで全文を確認した
- [ ] 既存テスト (特に `test_vector_store.py`, `test_rag_service.py`, `test_graphrag.py`) が Green であること
- [ ] `make lint` または `ruff check src tests` が通ること
- [ ] `make typecheck` または `mypy src/services/vector_store.py src/services/rag_service.py src/services/embedding_service.py` が通ること
- [ ] 新規テストは 1 ステップあたり 1〜3 関数のサイズ
- [ ] `__all__` / docstring / 型ヒントを更新した
- [ ] コミットメッセージは Conventional Commits 形式 (`feat(rag): ...` / `test(rag): ...` / `chore(rag): ...`)

## 4. ロールバック戦略

- Phase A (Step 1-10) は純粋追加なので `git revert` で完全復帰可能。
- Phase B (Step 11-20) で `requirements.txt` を変更した場合は、関連仮想環境を `pip install -r requirements.txt.lock` で復元。
- Phase E (Step 41-50) で `REQUIRE_PG=True` をデフォルト化する場合、いったん `False` のまま Step 50 で止め、別途フラグ `LEGACY_RAG_FALLBACK` で旧挙動を維持する。
- Phase F (Step 51-58) は `RERANKER_BACKEND="none"` をデフォルトに据えるので、機能導入時の性能劣化は発生しない。

## 5. 工数見積もり

| Phase | ステップ | 目安工数 (低性能 LLM 想定) |
|---|---|---|
| A: テスト・フラグ整備 | 1-10 | 0.5 人日 |
| B: 設定と依存 | 11-20 | 0.5 人日 |
| C: Embedding 強化 | 21-30 | 1.0 人日 |
| D: VectorStore 性能 | 31-40 | 1.0 人日 |
| E: pgvector 必須化 | 41-50 | 1.5 人日 |
| F: Reranking | 51-58 | 1.0 人日 |
| G: 性能・Docs | 59-60 | 0.5 人日 |
| **合計** | **60 ステップ** | **約 6.0 人日 ≒ 1.5 週** |

低性能 LLM でも 1 ステップ ≒ 30 分で実装可能な粒度に分割済み。
全 60 ステップを 1 PR ずつコミットすれば、レビューも容易で途中失敗時のロールバックも局所化できる。
