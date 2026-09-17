"""3層ローリング記憶ビルダー (v5.0 Step 15 & Step 16).

長編執筆（100話〜300話）でもコンテキスト長が爆発せず一定範囲内に収まるよう、
以下3層の情報を最適に圧縮・結合して執筆プロンプト用のコンテキストを構築する:

Layer 1: 【設定・世界観バイブル】 (核となる設定・キャラクター)
Layer 2: 【過去話の確定事実タイムライン】 (各話100字ダイジェストのウィンドウ制御)
Layer 3: 【直前エピソード本文】 (直近の文脈・台詞テンポ維持)
"""
from __future__ import annotations

from typing import Any, List, Optional, Union
import math


class RollingMemoryBuilder:
    """3層ローリング記憶コンテキストビルダー。

    Attributes:
        max_recent_digests: 保持する直近ダイジェストの最大件数（デフォルト: 30）
        max_prev_episode_chars: 直前話本文の最大文字数（デフォルト: 2500）
        preserve_initial_digests: 物語導入部（第1〜2話）のダイジェストを固定保持するか
    """

    def __init__(
        self,
        max_recent_digests: int = 30,
        max_prev_episode_chars: int = 2500,
        preserve_initial_digests: int = 2,
    ):
        self.max_recent_digests = max_recent_digests
        self.max_prev_episode_chars = max_prev_episode_chars
        self.preserve_initial_digests = preserve_initial_digests

    def _normalize_digest(self, item: Any) -> str:
        """ダイジェスト要素（str, dict, EpisodeDigestModel）を標準文字列に変換する。"""
        if isinstance(item, str):
            return item.strip()
        if isinstance(item, dict):
            ep = item.get("episode_num", item.get("ep", ""))
            text = item.get("digest_text", item.get("text", ""))
            prefix = f"第{ep}話: " if ep else ""
            return f"{prefix}{text}".strip()
        # EpisodeDigestModel
        ep = getattr(item, "episode_num", None)
        text = getattr(item, "digest_text", str(item))
        prefix = f"第{ep}話: " if ep is not None else ""
        return f"{prefix}{text}".strip()

    def filter_and_window_digests(self, past_digests: List[Any]) -> List[str]:
        """ダイジェストリストにウィンドウ制御を適用する。

        件数が `max_recent_digests` を超える場合:
        - 導入部 (最初の `preserve_initial_digests` 件) を保持
        - 中間部を省略表示 (「... [中略 N話分] ...」)
        - 直近の最新話を保持
        """
        if not past_digests:
            return []

        normalized = [self._normalize_digest(d) for d in past_digests if d]

        if len(normalized) <= self.max_recent_digests:
            return normalized

        # ウィンドウ分割
        init_count = min(self.preserve_initial_digests, len(normalized))
        recent_count = self.max_recent_digests - init_count
        omitted_count = len(normalized) - init_count - recent_count

        initial_part = normalized[:init_count]
        recent_part = normalized[-recent_count:] if recent_count > 0 else []

        result = []
        result.extend(initial_part)
        if omitted_count > 0:
            result.append(f"……（第{init_count + 1}話〜第{init_count + omitted_count}話の確定事実はアーカイブ保存中 / 省略）……")
        result.extend(recent_part)
        return result

    def truncate_prev_episode(self, prev_episode_text: str) -> str:
        """直前話の本文が長すぎる場合、末尾を優先してウィンドウ制限する。"""
        if not prev_episode_text:
            return "なし"

        cleaned = prev_episode_text.strip()
        if len(cleaned) <= self.max_prev_episode_chars:
            return cleaned

        # 直前の文脈が最も重要なので、末尾の文字数を残す
        truncated = cleaned[-self.max_prev_episode_chars:]
        return f"……（前略）\n{truncated}"

    def build_context(
        self,
        bible_summary: str,
        past_digests: List[Any],
        prev_episode_text: str,
    ) -> str:
        """3層ローリング記憶を結合してプロンプト用コンテキストを構築する。

        Args:
            bible_summary: Layer 1 世界観・設定・主要キャラクター情報
            past_digests: Layer 2 過去エピソードのダイジェスト一覧
            prev_episode_text: Layer 3 直前エピソードの本文

        Returns:
            プロンプトに注入可能なフォーマット済みコンテキスト文字列
        """
        bible_clean = bible_summary.strip() if bible_summary else "（世界観設定なし）"
        windowed_digests = self.filter_and_window_digests(past_digests)
        digests_str = "\n".join(windowed_digests) if windowed_digests else "なし"
        prev_text_clean = self.truncate_prev_episode(prev_episode_text)

        return (
            f"【設定・世界観バイブル】\n"
            f"{bible_clean}\n\n"
            f"【過去話の確定事実タイムライン】\n"
            f"{digests_str}\n\n"
            f"【直前エピソード本文】\n"
            f"{prev_text_clean}\n"
        )

    def estimate_tokens(self, text: str) -> int:
        """日本語テキストの概算トークン数を算出（日本語1文字 ≒ 約0.8〜1.2トークン）。"""
        if not text:
            return 0
        return math.ceil(len(text) * 1.1)

    def get_context_stats(
        self,
        bible_summary: str,
        past_digests: List[Any],
        prev_episode_text: str,
    ) -> dict[str, Any]:
        """各層の文字数と推定トークン数の統計情報を取得する。"""
        ctx = self.build_context(bible_summary, past_digests, prev_episode_text)
        windowed = self.filter_and_window_digests(past_digests)
        return {
            "total_chars": len(ctx),
            "estimated_tokens": self.estimate_tokens(ctx),
            "past_digests_count_raw": len(past_digests),
            "past_digests_count_windowed": len(windowed),
            "prev_episode_chars": len(prev_episode_text or ""),
        }
