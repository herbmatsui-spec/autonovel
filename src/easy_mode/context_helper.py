"""
コンテキストヘルパーモジュール
"""

import tiktoken
from typing import List
from src.easy_mode.models import EpisodeResult


def build_prev_context(episodes: List[EpisodeResult], context_window: int, context_window_min_reserve: int) -> str:
    """前話までの要約文脈構築（トークンベース）"""
    if not episodes:
        return "（第1話のため前話なし）"

    # トークンエンコーダーを初期化
    encoding = tiktoken.get_encoding("cl100k_base")
    
    # 利用可能なトークン数を計算（コンテキストウィンドウから予約領域を差し引く）
    max_tokens = context_window - context_window_min_reserve
    
    summaries = []
    tokens_used = 0
    
    # 直近3話から逆順で処理（新しい話から古い話へ）
    for ep in reversed(episodes[-3:]):
        # エピソードの要約テキストを作成
        summary_text = f"第{ep.episode_num}話: {ep.title} - "
        
        # エンコードしてトークン数を計算
        summary_tokens = len(encoding.encode(summary_text))
        
        # 残りトークンで利用可能なコンテンツ長を計算
        remaining_tokens = max_tokens - tokens_used - summary_tokens
        if remaining_tokens <= 0:
            # トークンが足りない場合はこの話をスキップ
            continue
            
        # コンテンツをトークンベースで切り捨て
        content_tokens = encoding.encode(ep.content)
        if len(content_tokens) > remaining_tokens:
            # トークン制限内で切り捨て
            truncated_tokens = content_tokens[:remaining_tokens]
            truncated_content = encoding.decode(truncated_tokens)
        else:
            truncated_content = ep.content
            
        # 最終的な要約テキストを作成
        final_summary = f"{summary_text}{truncated_content}..."
        
        # 実際のトークン数を再計算
        final_tokens = len(encoding.encode(final_summary))
        if tokens_used + final_tokens > max_tokens:
            # トークンオー则此話をスキップ
            continue
            
        summaries.insert(0, final_summary)  # 順序を保持するため先頭に挿入
        tokens_used += final_tokens
        
        # トークン制限に達したらループを抜ける
        if tokens_used >= max_tokens * 0.9:  # 90%で余裕を持たせる
            break

    return "\n\n".join(summaries)
