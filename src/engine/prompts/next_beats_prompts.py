"""Next Beats 3バリエーション分岐生成用プロンプト定義モジュール。"""
from __future__ import annotations

from src.models.editor import BranchType

NEXT_BEATS_SYSTEM_INSTRUCTION = """あなたは人気ライトノベルのストーリー構成プロデューサーです。
執筆された直前までの本文を受け取り、読者がページをめくる手を止められなくなる魅力的な「次のシーン展開（約300〜500文字）」を提案します。
各バリエーションの指示・温度感に従い、鮮烈な情景と台詞、次への引きを含めて執筆してください。
"""

BRANCH_PROMPTS: dict[BranchType, str] = {
    BranchType.ROYAL: """【展開タイプ: 王道・カタルシス (Royal / Heroic)】
・主人公の勇気、決断、潜在能力の開花、逆転の一撃など、読者が最もスカッとする痛快で熱い王道展開。
・直前の危機や困難に対し、正面から立ち向かうドラマを描いてください。
""",

    BranchType.TWIST: """【展開タイプ: サスペンス・どんでん返し (Twist / Suspense)】
・読者や主人公の予想を裏切る衝撃の事実、新たな敵の乱入、仲間の隠された思惑、予想外のトラップなど、緊迫感と謎が深まる急展開。
・「一体どうなってしまうのか」という強い引き（クリフハンガー）を作ってください。
""",

    BranchType.PSYCHOLOGY: """【展開タイプ: 心情深化・キャラクターの絆 (Psychology / Emotion)】
・激しい戦闘や事件の合間の静寂、キャラクター同士の繊細な掛け合い、過去の傷や本音の吐露、恋愛感情や信頼の芽生えを描く展開。
・読者がキャラクターに強く愛着を持てるエモーショナルなシーンにしてください。
""",
}

NEXT_BEATS_USER_PROMPT_TEMPLATE = """【直前までの本文抜粋】
{current_tail}

【作品ジャンル】
{genre}

【キャラクター状況】
{character_context}

{branch_instruction}

【出力指示】
以下の JSON 形式で出力してください：
```json
{{
  "title": "展開のキャッチーなタイトル",
  "summary": "この展開の概要・狙い（1〜2文）",
  "content": "生成された本文抜粋（300〜500文字程度）",
  "hook_text": "次のエピソードへの引き・クリフハンガー"
}}
```
"""
