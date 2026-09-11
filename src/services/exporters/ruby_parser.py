import re


def parse_ruby_to_xhtml(text: str) -> str:
    """カクヨム・なろう標準のルビ記法を XHTML `<ruby>親文字<rt>るび</rt></ruby>` に変換する (Step 38)。
    1. ｜親文字《るび》
    2. 漢字《るび》
    """
    # 1. ｜親文字《るび》
    text = re.sub(
        r"[｜|]([^《\r\n]+)《([^》\r\n]+)》",
        r"<ruby>\1<rt>\2</rt></ruby>",
        text,
    )
    # 2. 漢字のみ《るび》
    text = re.sub(
        r"([一-龠々〆ヵヶ]+)《([^》\r\n]+)》",
        r"<ruby>\1<rt>\2</rt></ruby>",
        text,
    )
    return text


def parse_bouten(text: str) -> str:
    """ライトノベルの傍点記法 《《強調文字》》 を `<span class="bouten">強調文字</span>` に変換する (Step 39)。"""
    return re.sub(
        r"《《([^》\r\n]+)》》",
        r'<span class="bouten">\1</span>',
        text,
    )
