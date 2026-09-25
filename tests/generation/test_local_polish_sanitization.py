"""
LocalPolisher のサニタイズ処理とリグレッション防止テスト (Step 10)
"""

import pytest
from unittest.mock import patch
from src.generation.local_polish import LocalPolisher, sanitize_polished_text


def test_sanitize_preambles_and_postscripts():
    """AI前置きとおしゃべりが綺麗に除去されること"""
    raw_ai_output = """承知いたしました。以下のように修正しました：
勇者はゆっくりと剣を抜いた。その切っ先は月光に輝いていた。
以上となります。ご参考になれば幸いです。"""

    cleaned = sanitize_polished_text(raw_ai_output)
    expected = "勇者はゆっくりと剣を抜いた。その切っ先は月光に輝いていた。"
    assert cleaned == expected


def test_sanitize_code_block():
    """```markdown ... ``` 等のコードブロックから本文が抽出されること"""
    raw_ai_output = "```\n夜風が冷たく吹き抜けた。\n```"
    cleaned = sanitize_polished_text(raw_ai_output)
    assert cleaned == "夜風が冷たく吹き抜けた。"


@patch("src.generation.local_polish.call_llm_api")
def test_polish_integrates_sanitized_text(mock_call):
    """LocalPolisher がサニタイズされたテキストで対象範囲を正しく置換すること"""
    mock_call.return_value = """了解しました。修正案：
「逃げるな！」と叫んだ。
いかがでしょうか。"""

    base_text = "少年は立ち尽くしていた。走った。しかし追いつかれた。"
    # "走った。" を "「逃げるな！」と叫んだ。" に置き換え
    start = base_text.index("走った。")
    end = start + len("走った。")

    polisher = LocalPolisher()
    result = polisher.polish(base_text, (start, end), "セリフを入れて緊迫感を出して")

    expected = "少年は立ち尽くしていた。「逃げるな！」と叫んだ。しかし追いつかれた。"
    assert result == expected
