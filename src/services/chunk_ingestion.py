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
) -> int:
    """``ChapterChunk`` のリストを埋め込み計算 → ベクトルストアに一括 upsert.

    Args:
        store: 任意の ``BaseVectorStore`` 実装 (Chroma / InMemory 等)
        chunks: ``content`` が設定済みのチャンクラスト
        collection: コレクション名
        batch_size: 埋め込みバッチサイズ

    Returns:
        登録したドキュメント数
    """
    if not chunks:
        return 0

    texts = [str(c.content) for c in chunks]
    vectors = embedding_service.embed_texts(texts, batch_size=batch_size)

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


__all__ = ["upsert_chunks"]
