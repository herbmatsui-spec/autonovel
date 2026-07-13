"""
prompts/plotting.py
プロット生成用の定数テンプレートを定義するモジュール。
"""


EMOTIONAL_HOOK_TEMPLATE = (
    "本話の刺さり: {one_line_intent}"
    "（目標tensionピーク: {target_tension_peak}/100、"
    "品質はこの感情に従属させること）"
)

SHARP_EDGE_PROPOSAL_TEMPLATE = """
以下のプロット概要から、削ってはいけない3つの角を提案せよ。
角の種類は以下のいずれかで、JSON配列形式で返すこと。

- ending_pullback: 結末の引き方（期待を裏切る余韻のある終わり方）
- protagonist_flaw: 主人公の1つの欠陥（共感を誘う弱点）
- abnormal_dialogue: 異常なセリフ（キャラクターを際立たせる非日常的な発言）

【重要な約束事項】
- `key_phrase`: 本文（プロット概要）から「直接引用」した20文字以内の句。
  quality化管理で磨かれても、この句本身的は本文に残ること。
  必ず実際の本文から引用すること。説明文や要約は禁止。
- `description`: 角の内容を200文字以内で説明的に記述（読み手的解釈OK）
- `preserve_on_quality_polish`: true

プロット概要:
{plot_summary}

出力形式:
[
  {{"edge_type": "ending_pullback", "description": "結末の具体的内容の説明（200字以内）", "key_phrase": "本文からの直接引用句（20文字以内）", "preserve_on_quality_polish": true}},
  ...
]

【出力例】
[
  {{"edge_type": "protagonist_flaw", "description": "優柔不断な性格が敵の陰謀を許す結果に", "key_phrase": "優柔不断な態度が裏目に", "preserve_on_quality_polish": true}},
  {{"edge_type": "ending_pullback", "description": "結末が期待外れの余韻で締めくくられる構造", "key_phrase": "余韻のある結末が待ち受ける", "preserve_on_quality_polish": true}}
]
"""

EARLY_ENTERTAINMENT_CHECK_TEMPLATE = """
以下のラフプロットと冒頭500字のみを読んで、**品質を一切評価せず、面白さのみ**を評価せよ。
文章の美しさ、構成の完璧さは無視し、生理的な興味・反応のみを答える。

【ラフプロット】
{rough_plot}

【冒頭500字】
{opening_500_chars}

以下のJSON形式で返すこと:
{{
  "interest_score": 0-100,
  "physiological_reaction": "涙/怒り/背筋/共感/無反応 等",
  "would_continue_reading": true/false,
  "feedback": "面白さに関するフィードバック（300文字以内）"
}}
"""
