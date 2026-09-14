from __future__ import annotations
from typing import Dict, Any
from pydantic import BaseModel, Field

class PlatformRule(BaseModel):
    max_chapter_chars: int = Field(100000, description="1話あたりの最大文字数制限")
    max_title_chars: int = Field(100, description="タイトル最大文字数制限")
    requires_ai_disclosure: bool = Field(True, description="AI利用明記・タグ付与要件の有無")
    allowed_ruby_syntax: str = Field("custom", description="サポートするルビ記法")
    prohibited_patterns: list[str] = Field(default_factory=list, description="禁止ワード・表現のパターン")
    notes: str = Field("", description="特記事項・ガイドラインメモ")

PLATFORM_COMPLIANCE_RULES: Dict[str, PlatformRule] = {
    "kakuyomu": PlatformRule(
        max_chapter_chars=100000,
        max_title_chars=100,
        requires_ai_disclosure=True,
        allowed_ruby_syntax="kanji《ruby》",
        prohibited_patterns=[],
        notes="カクヨムではAI利用作品のタグ付け・開示が推奨/自主企画対応となります。"
    ),
    "narou": PlatformRule(
        max_chapter_chars=100000,
        max_title_chars=100,
        requires_ai_disclosure=True,
        allowed_ruby_syntax="kanji(ruby)",
        prohibited_patterns=[],
        notes="小説家になろうではAI生成・支援に関するガイドラインに基づき適切な表記が必要です。R18表現はノクターン・ムーンライト等の別サイトへ分離。"
    ),
    "alphapolis": PlatformRule(
        max_chapter_chars=50000,
        max_title_chars=100,
        requires_ai_disclosure=True,
        allowed_ruby_syntax="kanji|ruby",
        prohibited_patterns=[],
        notes="アルファポリスの規約に準拠した文字数・表現チェック。"
    ),
    "kindle": PlatformRule(
        max_chapter_chars=500000,
        max_title_chars=200,
        requires_ai_disclosure=True,
        allowed_ruby_syntax="html",
        prohibited_patterns=[],
        notes="KDP（Kindle Direct Publishing）のAIコンテンツ開示要件に対応。"
    )
}

def get_platform_rule(platform: str) -> PlatformRule:
    return PLATFORM_COMPLIANCE_RULES.get(platform.lower(), PLATFORM_COMPLIANCE_RULES["kakuyomu"])
