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
        indent_enabled: bool = True,
    ) -> FormattedChapterPayload:
        """指定プラットフォーム向けに本文、ルビ、改行、字下げを正規化整形する。

        Args:
            title: 章タイトル
            body: 本文
            foreword: 前書き
            afterword: 後書き
            platform: 投稿先プラットフォーム (narou / kakuyomu / alphapolis)
            indent_enabled: 行頭全角字下げのON/OFF（カクヨム推奨: False）
        """
        plat = (platform or "narou").lower()
        cleaned_body = cls._clean_typography(body, indent_enabled=indent_enabled)

        # Step 11: カクヨム専用空行リズム（字下げなし・段落間1行空行）
        if plat == "kakuyomu":
            formatted_body = cls._to_kakuyomu_ruby(cleaned_body)
            if not indent_enabled:
                formatted_body = cls._apply_kakuyomu_line_rhythm(formatted_body)
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
    def _clean_typography(cls, text: str, indent_enabled: bool = True) -> str:
        """行頭全角スペース字下げおよび台詞開始の空行・字下げ正規化。

        Args:
            text: 対象テキスト
            indent_enabled: Falseの場合は行頭字下げを行わない（カクヨム推奨）
        """
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
            if indent_enabled and not content.startswith(cls.DIALOGUE_STARTERS):
                out.append(f"　{content}")
            else:
                # Step 10: 字下げ無効化（カクヨム推奨スタイル）
                out.append(content)

        # 連続空行を最大2行に制限
        res = "\n".join(out)
        return re.sub(r"\n{3,}", "\n\n", res)

    @classmethod
    def _apply_kakuyomu_line_rhythm(cls, text: str) -> str:
        """Step 11: カクヨム専用の空行リズム（字下げなし・段落間に自然な1行空行）。

        段落（空行で区切られた塊）間に1行空行を配置し、
        連続空行は2行までに正規化する。
        """
        if not text:
            return ""

        blocks = [b for b in re.split(r"\n{2,}", text.strip()) if b.strip()]
        if not blocks:
            return ""

        return "\n\n".join(blocks)

    @classmethod
    def split_dense_paragraphs(cls, text: str, max_lines: int = 3) -> str:
        """Step 12: スマホ読書用「3行超の段落自動分割（空行挿入）」。

        1段落が4行以上連続すると読者が圧迫感で離脱するため、
        句点（。）を基準に自動で改行＋空行を挟んで分割する。

        Args:
            text: 対象テキスト
            max_lines: 1段落あたりの許容行数（既定3行）

        Returns:
            str: 分割済みテキスト
        """
        if not text:
            return ""

        # 句点で区切られた文単位に分割（句点は保持）
        sentences = re.findall(r"[^。]+。?", text)
        if not sentences:
            return text

        paragraphs: list[list[str]] = []
        current: list[str] = []
        char_budget = 45 * max_lines  # 1行約45字（スマホ横幅）を基準にした文字数バジェット

        for sentence in sentences:
            current.append(sentence)
            # 文字バジェット超過、または句点で終わる文がmax_lines文連続したら分割
            if sum(len(s) for s in current) >= char_budget or len(current) >= max_lines:
                paragraphs.append(current)
                current = []

        if current:
            paragraphs.append(current)

        return "\n\n".join("".join(p) for p in paragraphs)

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
