"""
src/services/token_tracker.py — トークン使用量追跡サービス
"""

import time
from typing import Any

from src.models.report import TokenUsageReport


class TokenTracker:
    """トークン使用量を追跡するサービス"""

    def __init__(self):
        """初期状態を作成"""
        self.total_tokens = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.episode_count = 0
        self.episode_usages: list[dict[str, Any]] = []
        self.start_time: float | None = None
        self.end_time: float | None = None
        self.last_model_name: str | None = None
        self.last_agent_name: str | None = None

    def start(self):
        """追跡を開始"""
        self.start_time = time.time()

    def add_usage(
        self,
        input_tokens: int,
        output_tokens: int,
        ep_num: int | None = None,
        model_name: str | None = None,
        agent_name: str | None = None,
    ):
        """使用量を加算

        Args:
            input_tokens: 入力トークン数
            output_tokens: 出力トークン数
            ep_num: エピソード番号（任意）
            model_name: 使用モデル名（任意）
            agent_name: エージェント名（任意）
        """
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.total_tokens += input_tokens + output_tokens

        if model_name:
            self.last_model_name = model_name
        if agent_name:
            self.last_agent_name = agent_name

        if ep_num is not None:
            self.episode_usages.append(
                {
                    "ep_num": ep_num,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": input_tokens + output_tokens,
                    "model_name": model_name,
                    "agent_name": agent_name,
                }
            )

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
            generation_time_seconds=generation_time,
        )

    def get_episode_usages(self) -> list[dict[str, Any]]:
        """エピソード毎の使用量を取得

        Returns:
            List[Dict[str, Any]]: エピソード毎の使用量リスト
        """
        return self.episode_usages.copy()

    def reset(self):
        """状態をリセット"""
        self.total_tokens = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.episode_count = 0
        self.episode_usages = []
        self.start_time = None
        self.end_time = None
        self.last_model_name = None
        self.last_agent_name = None

    async def log_cost_consumption(
        self,
        book_id: int,
        agent_name: str,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
        chapter_number: int | None = None,
        session: Any = None,
    ) -> float | None:
        """LLM呼び出し完了時に ``CostLogModel`` へ自動コミットするフック。

        ``CostCalculator`` で推定コストを算出し、``session`` が渡された場合は
        ``CostLogModel`` レコードを作成して flush する。

        Args:
            book_id: 作品ID
            agent_name: エージェント名
            model_name: 使用モデル名
            input_tokens: 入力トークン数
            output_tokens: 出力トークン数
            chapter_number: 章番号（任意）
            session: 非同期DBセッション（任意）。未指定時はコストのみ返す。

        Returns:
            推定コスト（USD）。``session`` が未指定または flush 失敗時は ``None``。
        """
        from src.services.cost_analytics import CostCalculator

        cost_calculator = CostCalculator()
        cost_usd = cost_calculator.calculate(input_tokens, output_tokens, model_name)

        if session is None:
            return cost_usd

        from src.backend.database.models import CostLogModel

        log_entry = CostLogModel(
            book_id=book_id,
            chapter_number=chapter_number,
            agent_name=agent_name,
            model_name=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
        )
        try:
            session.add(log_entry)
            await session.flush()
        except Exception:
            import logging

            logging.getLogger(__name__).warning(
                "Failed to log cost consumption for book_id=%s", book_id, exc_info=True
            )
            return cost_usd
        return cost_usd
