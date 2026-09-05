SENSORY_EXPANSION_PROMPT = """
以下の本文中の抽象的な感情描写を、五感（視覚・聴覚・触覚・嗅覚・味覚）に訴える具体的な感覚描写に展開してください（Show, Don't Tell）。

【本文】
{original_text}

【検出された抽象的感情フレーズ】
{emotion_spans}

【感情→感覚マッピング参考】
{sensory_map}

【制約】
- 各抽象フレーズを 3-5 文の具体描写に置換
- 文体・視点・時制・キャラ口調を完全維持
- そのシーンの文脈（場所・状況・登場人物）に整合する感覚を選択
- 比喩・メタファーを効果的に使用
- 拡張後の文字数は元の約 {expansion_ratio} 倍を目安
- 味覚・嗅覚は控えめに（違和感がない場合のみ）

【出力形式】JSON:
{{
  "enriched_text": "感覚展開済み本文",
  "expansions": [
    {{"original_phrase": "彼は悲しかった", "expanded_text": "彼の頬を伝う冷たい涙が、石畳の凍りついた感覚を鋭く際立たせた。遠くから聞こえるサイレンの音が、彼の緊張をさらに高めていた。革の手袋のざらつきが、剣の柄をしっかりと捉えていることを伝えていた。", "emotion": "sadness", "senses_covered": ["visual", "auditory", "tactile"]}}
  ]
}}
"""