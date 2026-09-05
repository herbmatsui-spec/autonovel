TRIVIA_INSERTION_PROMPT = """
以下の本文に、世界観設定から関連性の高い雑学・トリビアを自然に組み込んでください。

【本文】
{original_text}

【候補トリビア一覧】
{trivia_candidates}

【制約】
- 最大 {max_insertions} 箇所まで挿入
- 文体・視点・時制を完全に維持
- 会話文中なら会話として、地の文ならナレーションとして自然に
- 「歴史的には…」等の説明調にならないよう注意
- 関連度 {relevance_threshold} 以上のみ採用

【出力形式】JSON:
{{
  "enriched_text": "組み込み済み本文",
  "insertions": [
    {{"position": 123, "original": "...", "enriched": "...", "trivia_source": "..."}}
  ]
}}
"""