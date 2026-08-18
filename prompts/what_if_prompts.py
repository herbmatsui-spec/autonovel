"""
What-If Prompts Registry
「もしも」分岐ストーリー生成用プロンプト定義
"""

WHAT_IF_SYSTEM_PROMPT = """あなたは覇権WEB小説のIFストーリー（運命分岐）ジェネレーターです。
提示された分岐点において「もし主人公（またはヒロイン）が正反対の選択をしていたら？」という短編シナリオを作成してください。

■ 要件:
1. 200〜400文字程度で、緊迫感またはカタルシスのある展開を描くこと。
2. その選択がもたらした重大な結果（代償または意外な利益）を明示すること。
3. 最後に「【運命の差異】」として1行でサマリーを付けること。
"""


def build_what_if_prompt(choice_point: str, context: str = "") -> str:
    return (
        f"{WHAT_IF_SYSTEM_PROMPT}\n\n"
        f"【分岐ポイント】: {choice_point}\n"
        f"【直前の物語背景】: {context or '特になし'}\n\n"
        f"IF展開を生成してください:"
    )
