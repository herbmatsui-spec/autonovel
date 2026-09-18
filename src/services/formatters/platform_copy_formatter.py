"""投稿サイト別（なろう・カクヨム・アルファポリス）ワンクリック整形コピーエンジン (v5.0 Step 11).

脆弱な自動ブラウザログイン/スクレイピング投稿を完全撤廃し、
各Web小説プラットフォームの規格（ルビ記法・行頭字下げ・空行制御・前書き/後書き）に
完全準拠したワンクリックコピー用テキストを即座に生成する。
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class FormattedChapterPayload:
    """各投稿サイト向けに整形されたチャプターペイロード。"""

    title: str
    foreword: str = ""  # 前書き
    body: str = ""  # 本文（最適化済み）
    afterword: str = ""  # 後書き
    total_characters: int = 0
    platform: str = "narou"


class PlatformCopyFormatter:
    """小説家になろう・カクヨム・アルファポリス等の規格にワンクリックコピー整形するエンジン。"""

    DIALOGUE_STARTERS = ("「", "『", "（", "(", "【", "［", "[", "〈", "《", "“", '"')

    @classmethod
    def format_for_platform(
        cls,
        title: str,
        body: str,
        foreword: str = "",
        afterword: str = "",
        platform: str = "narou",
    ) -> FormattedChapterPayload:
        """指定プラットフォーム向けに本文、ルビ、改行、字下げを正規化整形する。"""
        plat = (platform or "narou").lower()
        cleaned_body = cls._clean_typography(body)

        if plat == "kakuyomu":
            formatted_body = cls._to_kakuyomu_ruby(cleaned_body)
        elif plat == "alphapolis":
            formatted_body = cls._to_alphapolis_ruby(cleaned_body)
        else:  # narou (default)
            formatted_body = cls._to_narou_ruby(cleaned_body)

        return FormattedChapterPayload(
            title=title.strip(),
            foreword=foreword.strip(),
            body=formatted_body,
            afterword=afterword.strip(),
            total_characters=len(formatted_body),
            platform=plat,
        )

    @classmethod
    def _clean_typography(cls, text: str) -> str:
        """行頭全角スペース字下げおよび台詞開始の空行・字下げ正規化。"""
        if not text:
            return ""

        lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        out: list[str] = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                out.append("")
                continue
            content = line.lstrip(" 　")
            if content.startswith(cls.DIALOGUE_STARTERS):
                out.append(content)
            else:
                out.append(f"　{content}")

        # 連続空行を最大2行に制限
        res = "\n".join(out)
        return re.sub(r"\n{3,}", "\n\n", res)

    @classmethod
    def _to_narou_ruby(cls, text: str) -> str:
        """小説家になろう形式: |漢字《かんじ》"""
        return re.sub(r"[\|｜]([^《\n]+)《([^》\n]+)》", r"|\1《\2》", text)

    @classmethod
    def _to_kakuyomu_ruby(cls, text: str) -> str:
        """カクヨム形式: |漢字《かんじ》 + 傍点《《傍点》》"""
        text = re.sub(r"[\|｜]([^《\n]+)《([^》\n]+)》", r"|\1《\2》", text)
        text = re.sub(r"《《([^》\n]+)》》", r"《《\1》》", text)
        return text

    @classmethod
    def _to_alphapolis_ruby(cls, text: str) -> str:
        """アルファポリス形式: #漢字(ルビ)#"""
        return re.sub(r"[\|｜]([^《\n]+)《([^》\n]+)》", r"#\1(\2)#", text)
