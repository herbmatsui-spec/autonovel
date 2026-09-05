"""Simulate Character Reactions and Comments on Journals (Step 49)."""
from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from src.agents.social.models import JournalEntry, SocialComment, ReactionType

logger = logging.getLogger(__name__)


def simulate_character_reactions(
    journal: JournalEntry,
    other_characters: list[dict[str, Any]],
    llm: Any = None,
    max_reactions: int = 2,
) -> list[SocialComment]:
    """Simulate psychological reactions and comments from other characters on a journal entry."""
    if not other_characters:
        return []

    comments: list[SocialComment] = []
    author_id = journal.character_id
    author_name = journal.character_name

    candidates = [
        c for c in other_characters
        if str(c.get("id", c.get("name", ""))) != author_id
        and c.get("name") != author_name
    ]

    for char in candidates[:max_reactions]:
        c_id = str(char.get("id") or char.get("name", "char"))
        c_name = char.get("name", "登場人物")
        c_role = char.get("role", "登場人物")

        content = None
        reaction_type: ReactionType = "empathy"
        trust_delta = 0.0
        tension_delta = 0.0

        # 1. LLM 呼び出し試行
        if llm:
            try:
                prompt = f"""
あなたは小説の登場人物「{c_name}（役割: {c_role}）」です。
「{author_name}」が書いた以下の内面独白・日記を読んだ（またはその心情を察知した）とします。

【{author_name}の日記】
感情: {journal.emotion}
内容: {journal.content}

{c_name}としての素直なリアクション・コメント（心の中のつぶやき）を50〜100文字で出力してください。
また、反応タイプ（empathy / conflict / irony / support / suspicion）を1つ選択してください。

出力形式:
反応タイプ: [選択したタイプ]
コメント: [コメント本文]
"""
                resp = llm.generate(prompt) if hasattr(llm, "generate") else str(llm(prompt))
                if "コメント:" in resp:
                    lines = resp.split("\n")
                    for line in lines:
                        if line.startswith("反応タイプ:"):
                            t = line.replace("反応タイプ:", "").strip().lower()
                            if t in ["empathy", "conflict", "irony", "support", "suspicion"]:
                                reaction_type = t
                        elif line.startswith("コメント:"):
                            content = line.replace("コメント:", "").strip()
            except Exception as e:
                logger.debug(f"LLM reaction simulation failed for {c_name}: {e}")

        # 2. フォールバック生成（キャラクターの役割に基づくルールベース反応）
        if not content:
            if any(w in c_role for w in ["ライバル", "敵", "対立"]):
                reaction_type = "irony"
                content = f"口では綺麗事を並べても、現実は非情だ。貴様のその甘さがいつまで続くか見ものだな。"
                trust_delta = -5.0
                tension_delta = 10.0
            elif any(w in c_role for w in ["師匠", "導き手", "親友"]):
                reaction_type = "support"
                content = f"迷うことは恥ではない。その苦悩を抱えたまま、一歩前に進むのだ。"
                trust_delta = 10.0
                tension_delta = -5.0
            elif any(w in c_role for w in ["裏切り", "黒幕", "密定"]):
                reaction_type = "suspicion"
                content = f"ほう、そう考えていたのか。だがその焦りこそが、こちらの好機となる。"
                trust_delta = -15.0
                tension_delta = 15.0
            else:
                reaction_type = "empathy"
                content = f"その気持ち、分からなくもないよ。誰だって重い荷物を背負えば足が竦むものさ。"
                trust_delta = 5.0
                tension_delta = -2.0

        comment = SocialComment(
            comment_id=f"cmt_{journal.book_id}_{journal.ep_num}_{c_id}_{uuid.uuid4().hex[:6]}",
            journal_id=journal.entry_id,
            from_character_id=c_id,
            from_character_name=c_name,
            reaction_type=reaction_type,
            content=content,
            trust_delta=trust_delta,
            tension_delta=tension_delta,
            created_at=datetime.now(timezone.utc),
        )
        comments.append(comment)

    return comments


__all__ = ["simulate_character_reactions"]
