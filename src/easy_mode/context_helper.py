"""
コンテキストヘルパーモジュール
"""

import logging
from typing import List, Optional
from src.easy_mode.models import EpisodeResult

logger = logging.getLogger(__name__)

try:
    import tiktoken
except ImportError:
    tiktoken = None  # type: ignore


class _CharFallbackEncoding:
    """tiktokenが未インストールの環境用フォールバックエンコーダー"""

    def encode(self, text: str) -> list[int]:
        # 日本語等の概算: 1文字あたり約1.5トークン換算のダミーリスト
        return list(range(max(1, int(len(text) * 1.5))))

    def decode(self, tokens: list[int]) -> str:
        # トークン長に応じた文字数で切り詰め
        char_len = max(1, int(len(tokens) / 1.5))
        return ""  # 実際には decode 前の文字列からスライスするためヘルパー側でケア


def _get_encoding():
    if tiktoken is not None:
        try:
            return tiktoken.get_encoding("cl100k_base")
        except Exception:
            pass
    return None


def build_prev_context(
    episodes: List[EpisodeResult], context_window: int, context_window_min_reserve: int
) -> str:
    """前話までの要約文脈構築（トークンベース / フォールバック対応）"""
    if not episodes:
        return "（第1話のため前話なし）"

    encoding = _get_encoding()
    max_tokens = max(100, context_window - context_window_min_reserve)
    summaries: List[str] = []
    tokens_used = 0

    for ep in reversed(episodes[-3:]):
        summary_text = f"第{ep.episode_num}話: {ep.title} - "

        if encoding is not None:
            summary_tokens = len(encoding.encode(summary_text))
            remaining_tokens = max_tokens - tokens_used - summary_tokens
            if remaining_tokens <= 0:
                continue

            content_tokens = encoding.encode(ep.content)
            if len(content_tokens) > remaining_tokens:
                truncated_tokens = content_tokens[:remaining_tokens]
                truncated_content = encoding.decode(truncated_tokens)
            else:
                truncated_content = ep.content

            final_summary = f"{summary_text}{truncated_content}..."
            final_tokens = len(encoding.encode(final_summary))
        else:
            # tiktoken なしの文字数ベース概算
            char_budget = max(50, int(max_tokens / 1.5))
            if len(ep.content) > char_budget:
                truncated_content = ep.content[:char_budget]
            else:
                truncated_content = ep.content
            final_summary = f"{summary_text}{truncated_content}..."
            final_tokens = int(len(final_summary) * 1.5)

        if tokens_used + final_tokens > max_tokens:
            continue

        summaries.insert(0, final_summary)
        tokens_used += final_tokens

        if tokens_used >= max_tokens * 0.9:
            break

    return "\n\n".join(summaries)
