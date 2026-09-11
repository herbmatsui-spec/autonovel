import html
import re


def sanitize_novel_text(text: str) -> str:
    """約物禁則処理および全角三点リーダー等の正規化 (Step 41)。"""
    # 奇数個の三点リーダー（…）を偶数（2倍数）に揃える
    text = re.sub(r"(?<!…)…(?!…)", "……", text)
    # 奇数個のダッシュ（―）を偶数に揃える
    text = re.sub(r"(?<!―)―(?!―)", "――", text)
    # 行頭禁則: 行頭に来てしまった閉じ括弧や句読点の修正
    lines = text.splitlines()
    cleaned_lines = []
    for line in lines:
        cleaned_lines.append(line.rstrip())
    return "\n".join(cleaned_lines)


def escape_xhtml_text(text: str) -> str:
    """XHTML用の安全なXMLエスケープ"""
    return html.escape(text, quote=True)
