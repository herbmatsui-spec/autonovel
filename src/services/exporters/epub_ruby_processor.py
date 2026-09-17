"""Web小説ルビ・傍点・縦中横をEPUB 3 XHTML準拠タグへ高速変換するプロセッサ (v5.0 Step 16)."""
from __future__ import annotations

import html
import re


class EpubRubyProcessor:
    """Web小説のルビ表記・傍点・縦中横をEPUB 3 XHTMLタグへ変換する。"""

    @classmethod
    def to_xhtml_paragraphs(cls, text: str) -> str:
        """プレーンテキストを行単位でパースし、XHTML段落タグ列を生成する。"""
        if not text:
            return ""

        lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        xhtml_lines: list[str] = []

        for line in lines:
            line_str = line.strip()
            if not line_str:
                xhtml_lines.append('<p class="empty-line">&#160;</p>')
                continue

            escaped = html.escape(line_str)

            # 1. ルビ変換: |漢字《かんじ》 -> <ruby>漢字<rt>かんじ</rt></ruby>
            with_ruby = re.sub(
                r"[\|｜]([^《\n]+)《([^》\n]+)》",
                r"<ruby>\1<rt>\2</rt></ruby>",
                escaped,
            )

            # 2. 傍点・圏点変換: 《《強調》》 -> <span class="bouten">強調</span>
            with_bouten = re.sub(
                r"《《([^》\n]+)》》",
                r'<span class="bouten">\1</span>',
                with_ruby,
            )

            # 3. 2桁数字の縦中横 (tcy): 12, 99 (日本語文中でも確実にマッチする前後非数字条件)
            with_tcy = re.sub(
                r"(?<!\d)(\d{2})(?!\d)",
                r'<span class="tcy">\1</span>',
                with_bouten,
            )

            # 4. 感嘆符・疑問符の縦中横 (tcy): !?, !!, ??, ！？
            with_tcy = re.sub(
                r"([!?！？]{2})",
                r'<span class="tcy">\1</span>',
                with_tcy,
            )

            is_dialogue = line_str.startswith(("「", "『", "（", "(", "【", "［", "["))
            p_class = ' class="dialogue"' if is_dialogue else ""
            xhtml_lines.append(f"<p{p_class}>{with_tcy}</p>")

        return "\n".join(xhtml_lines)
