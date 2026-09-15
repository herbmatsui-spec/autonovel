import pytest
from src.agents.erotic.filter import EroticFilter

def test_erotic_filter_safe_text():
    filter_engine = EroticFilter()
    text = "二人は手をつなぎ、見つめ合った。"
    result = filter_engine.evaluate(text)
    assert result["is_compliant"] is True

def test_erotic_filter_flagged_text():
    filter_engine = EroticFilter()
    # 規約違反ワードの検知
    text = "未成年を対象とした禁止表現サンプル"
    result = filter_engine.evaluate(text)
    assert "flags" in result
