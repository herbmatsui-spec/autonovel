import re
import pytest

def convert_aozora_ruby(text: str) -> str:
    # 簡易ルビ変換ロジックテスト
    pattern = r"｜?([一-龠々]+)《([^》]+)》"
    return re.sub(pattern, r"<ruby>\1<rt>\2</rt></ruby>", text)

def test_ruby_conversion():
    src = "彼女は｜林檎《りんご》を食べた。"
    converted = convert_aozora_ruby(src)
    assert "<ruby>林檎<rt>りんご</rt></ruby>" in converted