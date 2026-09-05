CITATION_ATTACHMENT_PROMPT = """
以下の本文中の事実記述に対し、World Bible 設定資料から典拠を特定し、脚注マーカーを挿入してください。

【本文】
{original_text}

【検出された事実記述と候補ソース】
{claim_source_pairs}

【制約】
- 事実記述の直後に脚注マーカー [^n] を挿入
- 同一ソースへの複数参照は同一番号を使用
- 文体・視点・時制を変更しない
- 会話文への脚注挿入は避ける（地の文のみ）
- 設定に従いスタイル適用: {citation_style}

【出力形式】JSON:
{{
  "enriched_text": "脚注マーカー挿入済み本文",
  "bibliography": [
    {{"marker": 1, "source": "世界観設定書・巻I", "page": "p.23", "claim": "魔法システムAはMPを10消費する"}}
  ],
  "citations": [
    {{"position": 456, "marker": 1, "claim": "...", "source_ref": "..."}}
  ]
}}
"""