"""Multi-Perspective Character Journals Generator (Step 48)."""
from __future__ import annotations

import logging
import uuid
from typing import Any
from datetime import datetime, timezone

from src.agents.social.models import JournalEntry

logger = logging.getLogger(__name__)


def generate_multi_perspective_journals(
    scene_summary: str = "",
    characters: list[dict[str, Any]] | None = None,
    book_id: int = 1,
    ep_num: int = 1,
    scene_id: str = "",
    llm: Any = None,
    scene_text: str = "",
) -> list[JournalEntry]:
    """Generate distinct inner monologue / journal entries for multiple characters in the same scene."""
    characters = characters or []
    if not characters:
        return []

    effective_scene = scene_summary or scene_text
    scene_summary = effective_scene


import asyncio


async def _generate_single_journal_async(
    char: dict[str, Any],
    scene_summary: str,
    book_id: int,
    ep_num: int,
    scene_id: str,
    llm: Any = None,
) -> JournalEntry:
    """単一キャラクターの内面日記を生成（LLM呼び出しを非同期実行または非同期アダプタ対応）"""
    c_id = str(char.get("id") or char.get("name", "char"))
    c_name = char.get("name", "名無しの登場人物")
    c_role = char.get("role", "登場人物")
    c_traits = char.get("personality", "")

    content = None
    theme = "シーンの回顧"
    emotion = "思索"

    if llm:
        prompt = f"""
あなたは小説の登場人物「{c_name}」自身です。
以下のシーンを体験した直後に、あなただけの日記帳に誰にも見せない本音・内面独白を150〜200文字で執筆してください。

【あなたの立場・性格】
名前: {c_name}
立場・役割: {c_role}
性格・口調: {c_traits}

【起きたシーン】
{scene_summary}

日記本文のみを出力してください。
"""
        try:
            if hasattr(llm, "agenerate"):
                resp = await llm.agenerate(prompt)
            elif hasattr(llm, "generate_async"):
                resp = await llm.generate_async(prompt)
            elif hasattr(llm, "generate"):
                resp = await asyncio.to_thread(llm.generate, prompt)
            elif callable(llm):
                if asyncio.iscoroutinefunction(llm):
                    resp = await llm(prompt)
                else:
                    resp = await asyncio.to_thread(llm, prompt)
            else:
                resp = None

            if resp and len(str(resp).strip()) >= 20:
                content = str(resp).strip()
        except Exception as e:
            logger.debug(f"LLM journal generation failed for {c_name}: {e}")

    # フォールバック生成（キャラクター属性に応じた多面的独白）
    if not content:
        if any(w in c_role for w in ["主人公", "勇者", "正義"]):
            theme = "葛藤と決意"
            emotion = "使命感と不安"
            content = (
                f"今日の{scene_summary[:30]}の件、表面上は切り抜けられたが、"
                "自分の剣の未熟さを痛感した。誰かを犠牲にする選択肢だけは選ばない。"
                "明日こそは、誰も失わずに勝利する道を掴み取ってみせる。"
            )
        elif any(w in c_role for w in ["ライバル", "敵", "魔王", "対立"]):
            theme = "冷徹な観察"
            emotion = "苛立ちと野心"
            content = (
                f"ふん、{scene_summary[:30]}か。相変わらず甘い理想を振りかざしている。"
                "あの男の脆さはその偽善にある。力なき正義がいかに無力か、"
                "次の局面で骨の髄まで思い知らせてやる必要があるな。"
            )
        elif any(w in c_role for w in ["師匠", "賢者", "老練", "助言者"]):
            theme = "若者の成長"
            emotion = "慈愛と危惧"
            content = (
                f"{scene_summary[:30]}において、あの子の覚悟は本物だった。"
                "しかし、一人で背負い込む重荷はいずれその背を砕く。"
                "私が導けるのもそう長くはない。早く真の自立を促さねばならん。"
            )
        else:
            theme = "日常の所感"
            emotion = "好奇心"
            content = (
                f"{scene_summary[:30]}を間近で目撃した。"
                "風雲急を告げる気配がする。巻き込まれるのは御免だが、"
                "あの者たちの行く末にはどうしても興味を惹かれてしまう。"
            )

    return JournalEntry(
        entry_id=f"journal_{book_id}_{ep_num}_{c_id}_{uuid.uuid4().hex[:6]}",
        book_id=book_id,
        ep_num=ep_num,
        scene_id=scene_id,
        character_id=c_id,
        character_name=c_name,
        theme=theme,
        emotion=emotion,
        content=content,
        created_at=datetime.now(timezone.utc),
    )


async def generate_multi_perspective_journals_async(
    scene_summary: str = "",
    characters: list[dict[str, Any]] | None = None,
    book_id: int = 1,
    ep_num: int = 1,
    scene_id: str = "",
    llm: Any = None,
    scene_text: str = "",
) -> list[JournalEntry]:
    """各キャラクターの内面日記を asyncio.gather で並行生成する (Step 17)"""
    characters = characters or []
    if not characters:
        return []

    effective_scene = scene_summary or scene_text

    tasks = [
        _generate_single_journal_async(
            char=char,
            scene_summary=effective_scene,
            book_id=book_id,
            ep_num=ep_num,
            scene_id=scene_id,
            llm=llm,
        )
        for char in characters
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    valid_journals: list[JournalEntry] = []
    for r in results:
        if isinstance(r, JournalEntry):
            valid_journals.append(r)
        else:
            logger.error("Error generating journal entry: %s", r)

    return valid_journals


def generate_multi_perspective_journals(
    scene_summary: str = "",
    characters: list[dict[str, Any]] | None = None,
    book_id: int = 1,
    ep_num: int = 1,
    scene_id: str = "",
    llm: Any = None,
    scene_text: str = "",
) -> list[JournalEntry]:
    """Generate distinct inner monologue / journal entries for multiple characters in the same scene."""
    characters = characters or []
    if not characters:
        return []

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(
                asyncio.run,
                generate_multi_perspective_journals_async(
                    scene_summary=scene_summary,
                    characters=characters,
                    book_id=book_id,
                    ep_num=ep_num,
                    scene_id=scene_id,
                    llm=llm,
                    scene_text=scene_text,
                ),
            )
            return future.result()
    else:
        return asyncio.run(
            generate_multi_perspective_journals_async(
                scene_summary=scene_summary,
                characters=characters,
                book_id=book_id,
                ep_num=ep_num,
                scene_id=scene_id,
                llm=llm,
                scene_text=scene_text,
            )
        )


generate_scene_journals = generate_multi_perspective_journals
generate_scene_journals_async = generate_multi_perspective_journals_async

__all__ = [
    "generate_multi_perspective_journals",
    "generate_multi_perspective_journals_async",
    "generate_scene_journals",
    "generate_scene_journals_async",
]

