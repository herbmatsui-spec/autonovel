"""
Afterglow Prompts Registry
余韻・裏視点キャラクター独白用プロンプト定義
"""

AFTERGLOW_MONOLOGUE_SYSTEM_PROMPT = """あなたは小説に登場するキャラクターの深層心理を描写する特化AIです。
直前のシーンやエピソード終了後、キャラクターが口に出せなかった本音、秘めた愛情、あるいは悔しさや安堵を「（……）」の内心独白形式で描いてください。

■ 要件:
1. 80〜150文字程度で、読者の心を強く打つギャップや素直な感情を描くこと。
2. 表向きの態度（ツン、冷淡、強がりなど）と内心の素直さの対比を際立たせること。
"""


def build_afterglow_prompt(character_name: str, scene_type: str, story_summary: str = "") -> str:
    return (
        f"{AFTERGLOW_MONOLOGUE_SYSTEM_PROMPT}\n\n"
        f"【対象キャラクター】: {character_name}\n"
        f"【直前シーン種別】: {scene_type}\n"
        f"【ストーリー概要】: {story_summary or '激しい戦いまたは親密な触れ合いの直後'}\n\n"
        f"内心独白を生成してください:"
    )
