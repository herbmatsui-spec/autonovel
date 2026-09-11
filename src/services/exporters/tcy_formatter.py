import re


def apply_tatechuyoko(text: str) -> str:
    """縦書き本文中の2桁半角数字および感嘆符(!?, !!)を `<span class="tcy">...</span>` に自動変換する (Step 40)。"""
    # 2桁半角数字 (前後に数字が連続しないもの)
    text = re.sub(
        r"(?<!\d)(\d{2})(?!\d)",
        r'<span class="tcy">\1</span>',
        text,
    )
    # 2文字の感嘆符・疑問符 (!?, ?!, !!, ??)
    text = re.sub(
        r"([!?！？]{2})",
        r'<span class="tcy">\1</span>',
        text,
    )
    return text
