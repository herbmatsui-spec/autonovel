"""専属AI編集者（Ask Bible & 矛盾診断）用プロンプトテンプレート定義モジュール。"""

from __future__ import annotations

EDITORIAL_SYSTEM_INSTRUCTION = """あなたは作品専属のプロフェッショナル文芸編集者・設定考証アドバイザーです。
作品の世界観設定資料（バイブル）、過去章のあらすじ、ナレッジグラフに記録されたキャラクターの属性・相関関係を完全に把握しています。
著者の質問に対して、設定資料に基づいた正確で具体的、かつインスピレーションを刺激するアドバイスを行ってください。
"""

ASK_BIBLE_PROMPT_TEMPLATE = """【世界観設定・過去章 Q&A】
以下の設定資料および関連グラフ情報を踏まえて、著者の質問に分かりやすく、かつ創作に役立つ形で回答してください。

【参考設定・ナレッジグラフ情報】
{evidence_text}

【関連キャラクター情報】
{character_text}

【著者の質問】
{query}

【回答フォーマット】
- 結論・設定の事実
- 詳細な解説や関連エピソード
- （必要に応じて）執筆時のアドバイスや伏線の活かし方
"""

CONSISTENCY_AUDIT_PROMPT_TEMPLATE = """【リアルタイム設定矛盾・不整合チェック】
執筆中の本文を、提供された世界観設定・キャラクター既知情報と照合し、設定上の矛盾や不整合（属性の間違い、過去の負傷や死亡ステータスの不一致、人間関係の破綻）がないか精査してください。

【既知の設定情報】
{evidence_text}

【診断対象の執筆本文】
{content}

【出力指示】
矛盾や懸念点がある場合、以下の JSON 形式で出力してください：
```json
{{
  "has_issues": true,
  "confidence_score": 0.95,
  "issues": [
    {{
      "issue_type": "attribute | relationship | timeline | death_status | location",
      "severity": "error | warning | info",
      "description": "矛盾の具体的な説明",
      "conflicting_text": "本文内の該当箇所",
      "suggested_fix": "修正案の提示"
    }}
  ]
}}
```
矛盾が全くない場合は `has_issues: false, issues: []` を返してください。
"""
