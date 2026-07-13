"""
src/backend/engine_plot.py
プロット生成エンジンのラッパーモジュール。

感情起点（EmotionalHookSpec）をPlotから取得し、
プロンプト生成へ注入する責務を持つ。
"""
from __future__ import annotations

import json
import logging
from typing import Any, List, Optional

from pydantic import ValidationError

from config.sharp_edge_vocabulary import SHARP_EDGE_TYPES
from src.models.db import PlotDbModel
from src.models.emotional_hook import EmotionalHookSpec
from src.models.sharp_edge import SharpEdgeSpec

logger = logging.getLogger(__name__)


ENFORCE_ENTERTAINMENT_FIRST = True


def _build_default_hook() -> EmotionalHookSpec:
    """フック未設定時のデフォルト。UIのDEFAULT_DESIRES[0]=カタルシスに相当。"""
    return EmotionalHookSpec(
        hook_name="catharsis",
        one_line_intent="長い苦悩の末に訪れる解放と浄化",
        target_tension_peak=85,
    )


def resolve_emotional_hook(plot: Optional[PlotDbModel]) -> Optional[EmotionalHookSpec]:
    """
    Plot から emotional_hook を取得する。

    - Plot.emotional_hook_json が存在すればパースして返す。
    - Plot 自体が None または emotional_hook_json が空なら None を返す。
    - パース失敗時は None を返す。
    """
    if plot is None:
        return None

    raw = getattr(plot, "emotional_hook_json", None)
    if not raw:
        return None

    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return EmotionalHookSpec(**data)
    except Exception:
        logger.warning("emotional_hook_json のパースに失敗しました", exc_info=True)

    return None


async def get_emotional_hook_for_plot(
    plot: Optional[PlotDbModel],
    repo: Any,
    book_id: int,
    ep_num: int,
) -> EmotionalHookSpec:
    """
    プロット生成時に呼び出し、感情起点を決定して返す。

    優先順:
    1. Plot.emotional_hook_json が存在すればパース
    2. DB から Plot を取得して 1. を実施
    3. いずれもなければデフォルト(catharsis)を返す
    """
    hook = resolve_emotional_hook(plot)

    if hook is None and repo is not None:
        try:
            loaded = await repo.get_plot(book_id, ep_num)
            if loaded is not None:
                hook = resolve_emotional_hook(loaded)
        except Exception:
            logger.debug("Plot の load に失敗、デフォルトフックを使用", exc_info=True)

    if hook is None:
        if ENFORCE_ENTERTAINMENT_FIRST:
            logger.warning("emotional_hook 未設定、デフォルト(catharsis)で補完")
        return _build_default_hook()

    return hook


def ensure_emotional_hook_set(plot: Optional[PlotDbModel]) -> None:
    """
    面白さ先行モード時、Plot に emotional_hook が設定されていない場合は
    RuntimeError を送出し、感情設計を強制する。
    """
    if not ENFORCE_ENTERTAINMENT_FIRST:
        return
    hook = resolve_emotional_hook(plot)
    if hook is None:
        raise RuntimeError("面白さ先行モード: emotional_hook が未設定です")


def _parse_sharp_edges(raw: Optional[str]) -> List[SharpEdgeSpec]:
    """
    JSON文字列を List[SharpEdgeSpec] にパースする。失敗時は空リスト。
    """
    if not raw:
        return []
    try:
        data = json.loads(raw)
        if not isinstance(data, list):
            return []
        parsed = []
        for item in data:
            if not isinstance(item, dict):
                continue
            edge_type = item.get("edge_type", "")
            if edge_type not in SHARP_EDGE_TYPES:
                continue

            description = item.get("description", "").strip()
            key_phrase = item.get("key_phrase", "").strip()
            if len(key_phrase) > 20:
                logger.warning(f"key_phraseが20字を超えました: {key_phrase} → 先頭20文字を使用")
                key_phrase = key_phrase[:20]

            try:
                spec = SharpEdgeSpec(
                    edge_type=edge_type,
                    description=description,
                    key_phrase=key_phrase,
                    preserve_on_quality_polish=item.get("preserve_on_quality_polish", True)
                )
                parsed.append(spec)
            except ValidationError:
                continue
        return parsed
    except Exception:
        logger.warning("sharp_edges_json のパースに失敗しました", exc_info=True)
        return []


async def propose_sharp_edges(pm: Any, plot_summary: str) -> List[SharpEdgeSpec]:
    """
    プロット概要から「削ってはいけない3つの角」をLLMに提案させる。

    pm: PromptManager インスタンス
    plot_summary: プロット概要文字列

    戻り値: SharpEdgeSpec のリスト。パース失敗時は空リスト。
    """
    if pm is None:
        return []
    try:
        _ = await pm.build_sharp_edge_proposal_prompt(plot_summary)
        return []
    except Exception:
        logger.warning("尖り提案プロンプト生成に失敗しました", exc_info=True)
        return []


def resolve_sharp_edges(plot: Optional[PlotDbModel]) -> List[SharpEdgeSpec]:
    """
    Plot から sharp_edges を取得する。

    - Plot.sharp_edges_json が存在すればパースして返す。
    - PlotAnalytics.sharp_edges があればそれを返す。
    - いずれもなければ空リスト。
    """
    if plot is None:
        return []

    raw = getattr(plot, "sharp_edges_json", None)
    if raw:
        return _parse_sharp_edges(raw)

    return []


async def enforce_entertainment_gate(
    checker: Any,
    rough_plot: str,
    opening_chars: str,
    threshold: int = 60,
    max_retries: int = 2,
    regenerate_callback: Optional[Any] = None,
) -> "EntertainmentCheckResult":
    """
    プロット生成後、本文執筆の前に面白さ検証を実行する。

    ENFORCE_ENTERTAINMENT_FIRST が True で、最終 interest_score < threshold の場合は
    RuntimeError を送出し、基幹構造の再設計を要求する。
    """
    from src.backend.entertainment_loop import EntertainmentCheckResult, run_entertainment_first_loop

    result = await run_entertainment_first_loop(
        checker=checker,
        rough_plot=rough_plot,
        opening_chars=opening_chars,
        threshold=threshold,
        max_retries=max_retries,
        regenerate_callback=regenerate_callback,
    )

    if ENFORCE_ENTERTAINMENT_FIRST and result.interest_score < threshold:
        raise RuntimeError(
            f"面白さ検証不合格: interest_score={result.interest_score} < threshold={threshold}。基幹構造の再設計が必要"
        )

    return result
