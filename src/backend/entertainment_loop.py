"""
src/backend/entertainment_loop.py
早期面白さ検証ループ。

「面白さ検証 -> 興味不足なら基幹構造戻し -> 興味OKなら品質整備」の順序を強制する。
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from src.models.entertainment_check import EntertainmentCheckResult

logger = logging.getLogger(__name__)


DEFAULT_ENTERTAINMENT_THRESHOLD = 60
DEFAULT_MAX_RETRIES = 2


async def run_entertainment_first_loop(
    checker: Any,
    rough_plot: str,
    opening_chars: str,
    threshold: int = DEFAULT_ENTERTAINMENT_THRESHOLD,
    max_retries: int = DEFAULT_MAX_RETRIES,
    regenerate_callback: Optional[Any] = None,
    repo: Optional[Any] = None,
    book_id: Optional[int] = None,
    ep_num: Optional[int] = None,
) -> EntertainmentCheckResult:
    """
    早期面白さ検証を実行し、閾値を下回る場合は再生成を要求する。

    checker: EarlyEntertainmentChecker インスタンス
    rough_plot: ラフプロット文字列
    opening_chars: 冒頭500字文字列
    threshold: 合格ライン (0-100)
    max_retries: 再生成試行回数
    regenerate_callback: 再生成時に呼び出す非同期関数(引数: rough_plot) -> 新ラフプロット
    repo: リポジトリ（結果保存用）
    book_id: 書籍ID
    ep_num: エピソード番号

    戻り値: 最終の EntertainmentCheckResult
    """
    current_plot = rough_plot
    last_result: Optional[EntertainmentCheckResult] = None

    for attempt in range(max_retries + 1):
        result = await checker.check(current_plot, opening_chars)
        last_result = result
        logger.info(
            "早期面白さ検証 試行%d: interest_score=%d, would_continue_reading=%s",
            attempt + 1,
            result.interest_score,
            result.would_continue_reading,
        )

        if result.interest_score >= threshold and result.would_continue_reading:
            if repo and book_id is not None and ep_num is not None:
                try:
                    await repo.save_entertainment_check_log(
                        book_id=book_id,
                        ep_num=ep_num,
                        interest_score=result.interest_score,
                        physiological_reaction=result.physiological_reaction,
                        would_continue_reading=result.would_continue_reading,
                        feedback=result.feedback,
                    )
                except Exception:
                    logger.warning("entertainment_check_log の保存に失敗しました", exc_info=True)
            return result

        if attempt < max_retries and regenerate_callback is not None:
            try:
                current_plot = await regenerate_callback(current_plot)
                logger.info("基幹構造を再生成しました (試行%d)", attempt + 1)
            except Exception:
                logger.warning("再生成に失敗、現在の結果を返します", exc_info=True)
                break
        else:
            break

    if last_result is None:
        return EntertainmentCheckResult(
            interest_score=0,
            physiological_reaction="無反応",
            would_continue_reading=False,
            feedback="検証未実行",
        )

    if last_result.interest_score < threshold:
        logger.warning(
            "早期面白さ検証不合格: interest_score=%d < threshold=%d",
            last_result.interest_score,
            threshold,
        )
        if repo and book_id is not None and ep_num is not None:
            try:
                await repo.save_entertainment_check_log(
                    book_id=book_id,
                    ep_num=ep_num,
                    interest_score=last_result.interest_score,
                    physiological_reaction=last_result.physiological_reaction,
                    would_continue_reading=last_result.would_continue_reading,
                    feedback=last_result.feedback,
                )
            except Exception:
                logger.warning("entertainment_check_log の保存に失敗しました", exc_info=True)

    return last_result
