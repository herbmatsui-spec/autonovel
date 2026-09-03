"""小説本文のチャンク分割ユーティリティ."""

from __future__ import annotations

import re


def split_into_paragraphs(
    text: str, max_chunk_chars: int = 500, overlap_chars: int = 50
) -> list[str]:
    """小説本文を自然な改行・段落区切りを保ちつつチャンクに分割する.

    Args:
        text: 分割対象の小説テキスト
        max_chunk_chars: 1チャンクの最大文字数の目安
        overlap_chars: チャンク間のオーバーラップ文字数

    Returns:
        チャンク化されたテキストのリスト
    """
    if not text or not text.strip():
        return []

    # 空行（2つ以上の連続改行）で大まかに段落分割
    raw_paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]

    chunks: list[str] = []
    current_chunk: list[str] = []
    current_len = 0

    for paragraph in raw_paragraphs:
        p_len = len(paragraph)
        if current_len + p_len > max_chunk_chars and current_chunk:
            # 現在のチャンクを確定
            chunks.append("\n\n".join(current_chunk))
            current_chunk = [paragraph]
            current_len = p_len
        else:
            current_chunk.append(paragraph)
            current_len += p_len + 2  # 改行分の文字数

    if current_chunk:
        chunks.append("\n\n".join(current_chunk))

    return chunks


__all__ = ["split_into_paragraphs"]
