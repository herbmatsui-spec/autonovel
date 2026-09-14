"""
Cliffhanger Scorer for opening and ongoing episodes.
PLAN 02: 序盤3話特化型 ドーパミン注入・クリフハンガー強制エンジン
"""
from __future__ import annotations

import re
from src.config.opening_rules import (
    CLIFFHANGER_CRISIS_KEYWORDS,
    CLIFFHANGER_PEACEFUL_KEYWORDS,
    CLIFFHANGER_SHOCKING_KEYWORDS,
    CLIFFHANGER_TRIUMPH_KEYWORDS,
)
from src.models.opening_booster import CliffhangerEvaluation, CliffhangerType


def score_cliffhanger(text: str) -> CliffhangerEvaluation:
    """
    エピソードの末尾（ラスト150〜200文字）を解析し、
    クリフハンガー（次話への強烈な引き）の種別と強度を採点する。
    """
    if not text or not text.strip():
        return CliffhangerEvaluation(
            hook_type=CliffhangerType.PEACEFUL,
            score=0.0,
            reason="本文が空です。",
            tail_sentence="",
            requires_rewrite=True,
        )

    clean_text = text.strip()
    tail_chunk = clean_text[-200:]

    # 末尾の文を抽出
    sentences = re.split(r"[。\n]+", tail_chunk)
    valid_sentences = [s.strip() for s in sentences if s.strip()]
    tail_sentence = valid_sentences[-1] if valid_sentences else tail_chunk

    # 1. 平穏・就寝・安息のチェック（最優先で失格判定）
    peaceful_matches = [kw for kw in CLIFFHANGER_PEACEFUL_KEYWORDS if kw in tail_chunk]
    if peaceful_matches:
        return CliffhangerEvaluation(
            hook_type=CliffhangerType.PEACEFUL,
            score=35.0,
            reason=f"平穏な日常・就寝で終了しています（検知キーワード: {', '.join(peaceful_matches)}）。読者の離脱要因となるためリライトが必要です。",
            tail_sentence=tail_sentence,
            requires_rewrite=True,
        )

    # 各カテゴリーのマッチ数を集計
    crisis_matches = [kw for kw in CLIFFHANGER_CRISIS_KEYWORDS if kw in tail_chunk]
    shocking_matches = [kw for kw in CLIFFHANGER_SHOCKING_KEYWORDS if kw in tail_chunk]
    triumph_matches = [kw for kw in CLIFFHANGER_TRIUMPH_KEYWORDS if kw in tail_chunk]

    candidates: list[tuple[CliffhangerType, list[str], float, str]] = []

    if triumph_matches:
        score = min(100.0, 85.0 + len(triumph_matches) * 5.0)
        candidates.append((
            CliffhangerType.TRIUMPH_TRIGGER,
            triumph_matches,
            score,
            f"主人公の反撃予告や冷笑・覚醒で終わる爽快な引きです（検知: {', '.join(triumph_matches)}）。",
        ))

    if shocking_matches:
        score = min(100.0, 80.0 + len(shocking_matches) * 5.0)
        candidates.append((
            CliffhangerType.SHOCKING_TRUTH,
            shocking_matches,
            score,
            f"衝撃の事実判明や裏切りの露見で終わる強い引きです（検知: {', '.join(shocking_matches)}）。",
        ))

    if crisis_matches:
        score = min(100.0, 80.0 + len(crisis_matches) * 5.0)
        candidates.append((
            CliffhangerType.CRISIS,
            crisis_matches,
            score,
            f"急襲や絶体絶命の危機で終わる強い引きです（検知: {', '.join(crisis_matches)}）。",
        ))

    if candidates:
        # マッチ件数の多さ、次いでスコアの高さで最上位を選択
        candidates.sort(key=lambda x: (len(x[1]), x[2]), reverse=True)
        best_type, _, best_score, best_reason = candidates[0]
        return CliffhangerEvaluation(
            hook_type=best_type,
            score=best_score,
            reason=best_reason,
            tail_sentence=tail_sentence,
            requires_rewrite=False,
        )

    # 5. 語尾の記号判定（「！？」や「……」「――」など）
    if re.search(r"[！？!?…―—]$", tail_chunk.strip()):
        return CliffhangerEvaluation(
            hook_type=CliffhangerType.CRISIS,
            score=65.0,
            reason="含みを持たせた終わり方ですが、具体的な危機の描写や反撃の予告が不足しています。",
            tail_sentence=tail_sentence,
            requires_rewrite=True,
        )

    # いずれにも該当しない平坦な終わり方
    return CliffhangerEvaluation(
        hook_type=CliffhangerType.PEACEFUL,
        score=40.0,
        reason="話末に明確なフック（危機、新事実、反撃予告）がありません。平坦に終了しているためリライトが必要です。",
        tail_sentence=tail_sentence,
        requires_rewrite=True,
    )
