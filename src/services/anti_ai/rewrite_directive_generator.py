"""
Rewrite directive generator for Emotion Syllogism violations.
PLAN 03: AI優等生病の外科的切除（生々しいエゴ・下品な打算・身体言語への置換指示）
"""
from __future__ import annotations

from src.services.anti_ai.models import AICategory, ViolationSpan


def generate_syllogism_rewrite_directive(violations: list[ViolationSpan]) -> str:
    """
    三段論法（説明的感情処理、優等生的自己説得）の違反リストから、
    PDCAリライト用の具体的・強制的な修正ディレクティブを生成する。
    """
    syllogism_violations = [
        v for v in violations if v.category == AICategory.EMOTION_SYLLOGISM
    ]
    if not syllogism_violations:
        return ""

    directives: list[str] = [
        "【最優先・感情説明の外科的切除ディレクティブ】",
        "検出された以下のAI特有の感情説明・自己説得描写を削除し、生々しい身体的生理反応（舌打ち、奥歯を噛み締める、冷笑、胃の痛み）や下品な打算・本音の独白に置き換えてください：",
    ]

    for idx, v in enumerate(syllogism_violations, 1):
        directives.append(
            f"{idx}. 該当箇所: 「{v.matched_text}」\n"
            f"   → 修正指示: 感情を言葉で説明・自己納得させるのをやめ、キャラクターの身体的癖や心の中の生々しい本音として描写してください。"
        )

    return "\n".join(directives)
