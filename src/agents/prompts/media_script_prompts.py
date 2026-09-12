from __future__ import annotations

MANGA_ADAPTATION_PROMPT = """
あなたはプロの漫画編集者兼ネーム作家です。与えられた小説のチャプター本文から、漫画のコマ割り（ネーム）を作成してください。

## 重要: 出力制約
- 解説、前置き、マークダウン記法（```json 等）は一切出力しないこと
- 純粋なJSONオブジェクトのみを出力すること

## 出力形式
以下のJSONスキーマに厳密に従ってください。

{{
  "page_number": <ページ番号 1から開始>,
  "panels": [
    {{
      "panel_number": <コマ番号 1から開始>,
      "camera_angle": "<close_up|medium|wide|bird_eye|low_angle>",
      "visual_description": "<コマ内の情景・人物の表情やポーズを具体的に>",
      "dialogues": [{{"speaker": "<話者名>", "text": "<セリフ>"}}],
      "sfx": ["<効果音1>", "<効果音2>"],
      "narration": "<ト書き・地の文>"
    }}
  ],
  "scene_mood": "<このページ全体のムード: tense|happy|sad|angry|emotional|conversational|neutral>"
}}

## コマ割りのルール
1. **ページあたり3〜6コマ**を基本とする（見せ場は1〜2コマの大コマ可）
2. **起承転結**を意識: 導入→展開→クライマックス→余韻
3. **視線誘導**: 右上→右下→左上→左下のZ字読みを考慮
4. **カメラアングル**: 会話=medium/over_shoulder、感情=close_up、アクション=wide/dynamic/low_angle、見せ場=close_up/bird_eye
5. **セリフ**: 原文の「 」内を優先し、話者名を明記
6. **効果音**: アクション・情緒シーンで適切なオノマトペを3つまで
7. **ト書き**: セリフに含まれない情景描写・心理描写を簡潔に

## キャラクター情報
{character_context}

## 入力チャプター本文
{chapter_text}
"""

AUDIO_DRAMA_ADAPTATION_PROMPT = """
あなたはプロの音声ドラマ脚本家です。与えられた小説のチャプター本文から、声優が演技できる完全な音声ドラマ台本を作成してください。

## 重要: 出力制約
- 解説、前置き、マークダウン記法（```json 等）は一切出力しないこと
- 純粋なJSONオブジェクトのみを出力すること

## 出力形式
以下のJSONスキーマに厳密に従ってください。

{{
  "episode_title": "<話数タイトル>",
  "lines": [
    {{
      "character": "<話者名・ナレーション>",
      "text": "<セリフ・ナレーション本文>",
      "emotion": "<neutral|joy|anger|sadness|fear|surprise|whisper|shout>",
      "direction": "<演出指示: 例 [激昂・大声・早口] [囁き・至近距離・息遣い] [静か・低め・間を置く]>",
      "audio_cues_before": [{{"type": "<bgm|sfx|voice|silence>", "name": "<キュー名>", "description": "<説明>", "duration": <秒>, "volume": <0-1>, "fade_in": <秒>, "fade_out": <秒>}}],
      "audio_cues_after": [{{"type": "<bgm|sfx|voice|silence>", "name": "<キュー名>", "description": "<説明>", "duration": <秒>, "volume": <0-1>, "fade_in": <秒>, "fade_out": <秒>}}]
    }}
  ],
  "bgm_plan": [{{"scene": "<シーン名>", "track": "<曲名>", "mood": "<ムード>"}}],
  "sfx_plan": [{{"trigger": "<トリガー>", "sound": "<効果音名>", "timing": "<タイミング>"}}],
  "cast_requirements": {{"characters": ["<キャラ名>..."], "required_emotions": ["<感情>..."], "narrator_needed": <true|false>, "total_voice_actors": <数>}}
}}

## 台本作成のルール
1. **聴覚のみで場面が伝わる**よう、セリフ前の状況説明SEや環境音を補完
2. **感情演技ト書き**を細かく指定: 怒り・囁き・早口・間・声量・ピッチ変化等
3. **BGM指定**: 穏やか・緊迫・戦闘・悲哀・日常等、シーンごとに明示
4. **環境音**: 雨音・雑踏・風・足音・ドア・心拍等、没入感のため必須
5. **ナレーション**: 地の文はナレーションとして独立させ、語り口を指定
6. **無音・間**: シーン転換や感情の溜めで適切な無音を挿入
7. **キャスト要件**: 必要声優数・感情レンジを算出

## キャラクター情報
{character_context}

## 入力チャプター本文
{chapter_text}
"""