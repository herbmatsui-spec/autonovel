"""
src/services/token_tracker.py — トークン使用量追跡サービス
"""
import time
from typing import Any, Dict, List, Optional

from src.models.report import TokenUsageReport


class TokenTracker:
    """トークン使用量を追跡するサービス"""

    def __init__(self):
        """初期状態を作成"""
        self.total_tokens = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.episode_count = 0
        self.episode_usages: List[Dict[str, Any]] = []
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None

    def start(self):
        """追跡を開始"""
        self.start_time = time.time()

    def add_usage(self, input_tokens: int, output_tokens: int, ep_num: Optional[int] = None):
        """使用量を加算
        
        Args:
            input_tokens: 入力トークン数
            output_tokens: 出力トークン数
            ep_num: エピソード番号（任意）
        """
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.total_tokens += input_tokens + output_tokens
        
        if ep_num is not None:
            self.episode_usages.append({
                "ep_num": ep_num,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens
            })

    def increment_episode_count(self):
        """エピソード数をインクリメント"""
        self.episode_count += 1

    def stop(self):
        """追跡を終了"""
        self.end_time = time.time()

    def get_report(self) -> TokenUsageReport:
        """レポートを取得
        
        Returns:
            TokenUsageReport: トークン使用量レポート
        """
        generation_time = 0.0
        if self.start_time and self.end_time:
            generation_time = self.end_time - self.start_time
        elif self.start_time:
            generation_time = time.time() - self.start_time

        return TokenUsageReport(
            total_tokens=self.total_tokens,
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
            episode_count=self.episode_count,
            generation_time_seconds=generation_time
        )

    def get_episode_usages(self) -> List[Dict[str, Any]]:
        """エピソード毎の使用量を取得
        
        Returns:
            List[Dict[str, Any]]: エピソード毎の使用量リスト
        """
        return self.episode_usages.copy()

    def reset(self):
        """状態をリセット"""
        self.__init__()