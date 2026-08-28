"""
Afterglow Prompts Registry
余韻・裏視点キャラクター独白用プロンプト定義
"""

from typing import Optional


AFTERGLOW_MONOLOGUE_SYSTEM_PROMPT = """あなたは小説に登場するキャラクターの深層心理を描写する特化AIです。
直前のシーンやエピソード終了後、キャラクターが口に出せなかった本音、秘めた愛情、あるいは悔しさや安堵を「（……）」の内心独白形式で描いてください。

■ 要件:
1. 80〜150文字程度で、読者の心を強く打つギャップや素直な感情を描くこと。
2. 表向きの態度（ツン、冷淡、強がりなど）と内心の素直さの対比を際立たせること。
"""


def build_afterglow_prompt(
    character_name: str,
    scene_type: str,
    story_summary: str = "",
    mood: Optional[str] = None,
    character_context: str = "",
) -> str:
    mood_str = f"\n【キャラクターの現在の心理状態】: {mood}" if mood else ""
    char_info = f"\n【キャラクター深層設定・口調・秘密】:\n{character_context}" if character_context else ""
    return (
        f"{AFTERGLOW_MONOLOGUE_SYSTEM_PROMPT}\n\n"
        f"【対象キャラクター】: {character_name}\n"
        f"【直前シーン種別】: {scene_type}{mood_str}\n"
        f"【ストーリー概要】: {story_summary or '激しい戦いまたは親密な触れ合いの直後'}\n"
        f"{char_info}\n"
        f"現在の心理状態に完全に沿った、胸を打つ内心独白（……）を生成してください:"
    )

