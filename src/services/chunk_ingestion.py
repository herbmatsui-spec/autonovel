"""チャンク埋め込みの一括 upsert ヘルパ."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.services.embedding_service import embedding_service

if TYPE_CHECKING:
    from src.services.vector_store import BaseVectorStore
    from src.infrastructure.database.models.chunk import ChapterChunk


async def upsert_chunks(
    store: "BaseVectorStore",
    chunks: list["ChapterChunk"],
    collection: str,
    batch_size: int = 64,
    session: Any | None = None,
) -> int:
    """``ChapterChunk`` のリストを埋め込み計算 → ベクトルストア & DB embedding カラムに一括保存 (Step 26).

    Args:
        store: 任意の ``BaseVectorStore`` 実装 (Chroma / InMemory 等)
        chunks: ``content`` が設定済みのチャンクリスト
        collection: コレクション名
        batch_size: 埋め込みバッチサイズ
        session: オプションの SQLAlchemy セッション（渡された場合は自動 commit）

    Returns:
        登録したドキュメント数
    """
    if not chunks:
        return 0

    texts = [str(c.content) for c in chunks]
    vectors = await embedding_service.embed_texts_async(texts, batch_size=batch_size)

    # Step 26: 各 ChapterChunk の embedding カラムに事前保存
    for c, vec in zip(chunks, vectors):
        c.embedding = vec

    if session is not None:
        try:
            session.commit()
        except Exception:
            session.rollback()
            raise

    ids = [str(c.id) for c in chunks]
    metadatas: list[dict[str, Any]] = []
    for c in chunks:
        meta: dict[str, Any] = {
            "chapter_id": c.chapter_id,
            "chunk_index": c.chunk_index,
        }
        if c.chunk_metadata:
            meta.update(c.chunk_metadata)
        metadatas.append(meta)

    await store.add_documents(
        collection_name=collection,
        ids=ids,
        documents=texts,
        embeddings=vectors,
        metadatas=metadatas,
    )
    return len(chunks)


async def backfill_missing_embeddings(
    session: Any,
    store: "BaseVectorStore" | None = None,
    collection: str | None = None,
    batch_size: int = 64,
) -> int:
    """未計算 (embedding is None) の既存チャンクを検出し、一括で Embedding をバックフィルする (Step 27).

    Args:
        session: SQLAlchemy DB セッション
        store: オプションのベクトルストア
        collection: オプションのコレクション名
        batch_size: 埋め込み計算バッチサイズ

    Returns:
        バックフィル完了件数
    """
    from src.infrastructure.database.models.chunk import ChapterChunk

    all_chunks = session.query(ChapterChunk).all()
    missing_chunks = [c for c in all_chunks if not c.embedding or not isinstance(c.embedding, (list, tuple)) or len(c.embedding) == 0]

    if not missing_chunks:
        return 0

    total_backfilled = 0
    for i in range(0, len(missing_chunks), batch_size):
        batch = missing_chunks[i : i + batch_size]
        texts = [str(c.content) for c in batch]
        vectors = await embedding_service.embed_texts_async(texts, batch_size=len(texts))

        for c, vec in zip(batch, vectors):
            c.embedding = vec

        total_backfilled += len(batch)

    session.commit()
    return total_backfilled


__all__ = ["upsert_chunks", "backfill_missing_embeddings"]
