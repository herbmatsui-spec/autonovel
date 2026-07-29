"""
Prompt definitions and template management module for Gemini OCR and Summarizer.
"""

from enum import Enum
from typing import Dict, Any

class DocumentMode(Enum):
    MANUAL = "manual"
    BUSINESS = "business"

PROMPT_TEMPLATES: Dict[DocumentMode, Dict[str, str]] = {
    DocumentMode.MANUAL: {
        "title_prompt": """
以下の手書きマニュアルテキストの内容を読み取り、初心者に分かりやすい適切な「マニュアルのタイトル」を1つ生成してください。
記号や余計な解説は省き、タイトル名のみを出力してください。

テキスト:
{text}
""",
        "summary_prompt": """
以下の手書きマニュアルテキストを、初心者にも理解しやすいように要点整理・構造化してください。

【出力フォーマット要求】
1. 概要: 全体の目的や概要を3〜4文でわかりやすく説明
2. 要点（箇条書き）: 重要なポイントを3〜5個の箇条書きで抽出
3. 詳細セクション: 内容を論理的な章・節に分け、分かりやすい見出しと本文を作成

テキスト:
{text}
""",
        "glossary_prompt": """
以下のテキストから、初心者や新人にとって難解と思われる専門用語や業界用語を抽出し、分かりやすい説明（1〜2文）をつけてください。
専門用語がない場合は「なし」と答えてください。

テキスト:
{text}
"""
    },
    DocumentMode.BUSINESS: {
        "title_prompt": """
以下のビジネスドキュメントの内容を読み取り、内容を的確かつ簡潔に表す適切な「標準業務文書のタイトル」を1つ生成してください。
記号や余計な解説は省き、タイトル名のみを出力してください。

テキスト:
{text}
""",
        "summary_prompt": """
以下の標準業務文書を、ビジネス文書として適切なフォーマットで要約・構造化してください。

【出力フォーマット要求】
1. 概要: 文書の目的・背景・結論を明確かつ簡潔に記述
2. 要点: 意思決定に必要な主要事項や数値を箇条書きで整理
3. 詳細セクション: 論理的構造（背景、課題、対応策、スケジュール等）に基づき整理

テキスト:
{text}
""",
        "glossary_prompt": """
以下のテキストから、社内用語や略語、専門用語を抽出し、定義および解説を作成してください。

テキスト:
{text}
"""
    }
}

def get_prompt(mode: DocumentMode, prompt_type: str, **kwargs) -> str:
    """
    Retrieve and format prompt string by mode and type.
    """
    templates = PROMPT_TEMPLATES.get(mode, PROMPT_TEMPLATES[DocumentMode.MANUAL])
    template = templates.get(prompt_type, "")
    return template.format(**kwargs)
