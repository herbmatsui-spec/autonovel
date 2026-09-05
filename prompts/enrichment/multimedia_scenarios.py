MULTIMEDIA_SCENARIO_PROMPT = """
以下の重要シーンから、指定フォーマットの派生シナリオを生成してください。

【シーン本文】
{scene_text}

【シーン情報】
- タイプ: {scene_type}
- 登場人物: {characters}
- 緊張度: {tension_level}/10
- 文脈: {context_summary}

【出力フォーマット: {format}】
{format_instructions}

【制約】
- 本文のセリフ・アクション・感情を忠実に反映
- フォーマット固有の記法・構造を遵守
- カメラワーク・音響・コマ割り等は専門的観点で設計
- キャラクターの口調・性格を維持

【出力形式】JSON:
{{
  "format": "{format}",
  "scenario": {format_output_structure},
  "metadata": {{"scene_type": "{scene_type}", "duration_estimate_sec": 120}}
}}
"""

# フォーマット別詳細指示（テンプレート内で {format_instructions} に展開）
FORMAT_INSTRUCTIONS = {
    "manga_script": """
マンガ台本形式:
- パネル単位で構成（1ページ 4-6 コマ想定）
- 各コマ: コマ番号、画面描写、セリフ、効果音、カメラ指示
- 例: {{"panel": 1, "visual": "主人公が剣を構えるクローズアップ", "dialogue": "\"行くぞ\"", "sfx": "キーン", "camera": "低角度、顔アップ"}}
""",
    "radio_drama": """
ラジオドラマ台本形式:
- キュー番号、音響効果、ナレーション、セリフ、声優演技指示
- 例: {{"cue": 1, "sfx": "風の音、遠くで剣が交わる音", "narration": "夜風が二人を包む", "dialogue": [{"character": "主人公", "line": "行くぞ", "direction": "低く、決意を込めて"}]}, "bgm": "緊張感のある弦楽器"}}
""",
    "anime_storyboard": """
アニメ絵コンテ形式:
- カット番号、秒数、カメラ、アクション、セリフ、背景、作画指示
- 例: {{"cut": 1, "duration_sec": 3.5, "camera": "パン・左から右", "action": "主人公が剣を抜く", "dialogue": "行くぞ", "background": "月夜の廃墟", "animation_note": "髪と衣装が風になびく"}}
""",
    "live_action_shots": """
実写ショットリスト形式:
- シーンスラッグ、ショットタイプ、レンズ、カメラ移動、出演者、VFXメモ
- 例: {{"scene_slug": "EXT. 廃墟 - 夜", "shot_type": "ミディアムショット", "lens": "35mm", "movement": "スタビライザー追従", "actors": ["主人公"], "vfx": "剣の光エフェクト", "dialogue": "行くぞ"}}
"""
}

# フォーマット別出力構造（テンプレート内で {format_output_structure} に展開）
FORMAT_OUTPUT_STRUCTURES = {
    "manga_script": "List[Dict[panel, visual, dialogue, sfx, camera]]",
    "radio_drama": "List[Dict[cue, sfx, narration, dialogue[List[character, line, direction]], bgm]]",
    "anime_storyboard": "List[Dict[cut, duration_sec, camera, action, dialogue, background, animation_note]]",
    "live_action_shots": "List[Dict[scene_slug, shot_type, lens, movement, actors, vfx, dialogue]]"
}