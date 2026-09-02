# RAG / VectorStore セットアップガイド

このドキュメントは AutoNovel の VectorStore + RAG 検索サービス (`src/services/vector_store.py`,
`src/services/rag_service.py`, `src/services/embedding_service.py`,
`src/services/reranker.py`) のセットアップと運用手順をまとめたものです。

## 1. 必須 / 任意の依存

| パッケージ | 用途 | 必須化方法 |
|---|---|---|
| `chromadb >= 1.5.0` | ベクトル DB (HNSW + BM25) | `REQUIRE_CHROMA=true` |
| `rank-bm25 >= 0.2.2` | キーワード検索 | `chromadb` と一緒 |
| `pgvector >= 0.3.0` | PostgreSQL + ベクトル検索 | `REQUIRE_PG=true` |
| `sentence-transformers >= 2.6.0` | Cross-Encoder reranking | `RERANKER_BACKEND=cross_encoder` |

開発インストール:

```bash
pip install -e ".[rag]"      # RAG フルセット
pip install -e ".[dev]"      # テスト・Lint ツール
```

`chromadb` / `pgvector` がインストールされていない環境では `InMemoryFallbackStore`
(ブルートフォース・コサイン, デフォルト 10k 件上限) と SQLite フォールバックが
自動選択されます。`REQUIRE_*=true` にすると未インストール時に起動時 `RuntimeError`
で fail-fast します。

## 2. 環境変数 (.env)

```ini
# RAG モード: auto / chroma / memory
AUTONOVEL_RAG_MODE=auto

# 必須化 (Opt-in)
REQUIRE_CHROMA=false
REQUIRE_PG=false

# 不在時のフォールバック (memory / error)
RAG_FALLBACK_MODE=memory

# 埋め込みバッチサイズ
RAG_BATCH_SIZE=64

# Reranker
RERANKER_BACKEND=none                # none / simple / cross_encoder
RERANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2

# ChromaDB
CHROMA_DB_PATH=storage/chroma_db
CHROMA_HOST=
CHROMA_PORT=8000
```

## 3. マイグレーション

PostgreSQL + pgvector 環境では Alembic マイグレーションを適用してください:

```bash
alembic upgrade head
```

新規追加された `0003_pgvector_chapter_chunks` は `CREATE EXTENSION vector;` と
`ivfflat` インデックスの作成を行います。SQLite では no-op です。

## 4. トラブルシューティング

### `HAS_CHROMA=False` が出る

```bash
pip install -e ".[rag]"           # RAG 依存を一括導入
python -c "import chromadb; print(chromadb.__version__)"
```

それでも出るときは、ChromaDB が依存する `onnxruntime` 等の C 拡張のビルド失敗が
考えられます。`apt-get install -y build-essential` の後にもう一度 `pip install`
してください。

### `RAG_FALLBACK_MODE=error` で起動失敗する

`REQUIRE_CHROMA=true` / `REQUIRE_PG=true` のまま片方しか満たしていないケースです。
両方とも満たすか、`RAG_FALLBACK_MODE=memory` に切り替えてください。

### 起動が遅い

- `RAG_BATCH_SIZE` を増やす (例: 128)
- `RERANKER_BACKEND=none` にする (Cross-Encoder はモデルロードで 1-3 秒)
- ChromaDB を HTTP モード (`CHROMA_HOST=...`) に切替えて永続化クライアントを再利用

## 5. ベンチマーク目安 (100 チャンク, InMemoryFallbackStore)

| メトリック | 値 (目安) |
|---|---|
| `embed_texts(100)` | < 0.5 s (擬似埋め込み) |
| `add_documents(100)` | < 0.1 s |
| `search(top_k=10)` | < 0.01 s |

これらは InMemory + 擬似埋め込みでの値です。実 API を使う場合は
OpenAI のラウンドトリップが支配的になります。`tests/perf/test_vector_store_perf.py`
で計測できます:

```bash
pytest -m perf tests/perf/ -v -s
```

## 6. Reranker バックエンドの選択指針

| バックエンド | 速度 | 精度 | 依存 |
|---|---|---|---|
| `none` | ◎ (順) | ベースライン | なし |
| `simple` | ◯ (埋め込み) | ◯ | OpenAI API キー |
| `cross_encoder` | △ (モデル推論) | ◎ | `sentence-transformers` |

プロトタイピングは `simple`、本番品質は `cross_encoder` を推奨。

## 7. コレクション一覧

| CollectionType | 用途 |
|---|---|
| `SEMANTIC_CACHE` | 意味的キャッシュ |
| `STYLE_MEMORY` | 文体・文調 RAG |
| `WORLD_MEMORY` | 世界観・設定 RAG |
| `CHARACTER_MEMORY` | キャラクター RAG |
| `NARRATIVE_MEMORY` | 物語構造 RAG |
| `EPISODE_MEMORY` | エピソード本文 RAG |

監査 CLI:

```bash
python scripts/audit_vector_coverage.py --exit-on-fail
```
