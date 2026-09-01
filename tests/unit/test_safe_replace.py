from src.services.safe_replace import SafeReplacer


def test_safe_replacer_basic():
    """基本置換の検証。"""
    replacer = SafeReplacer({"勇者": "勇気ある少年", "魔王": "闇の支配者"})
    res = replacer.replace("勇者は魔王に立ち向かった。")
    assert res == "勇気ある少年は闇の支配者に立ち向かった。"


def test_safe_replacer_avoids_cascade_replacement():
    """順次置換による意図しない多重置換を防止できることの検証。"""
    # "A" -> "B", "B" -> "C" の場合、順次だと "A" -> "B" -> "C" になってしまうが、
    # SafeReplacer では 1パス置換により "A" は "B" に留まる。
    replacer = SafeReplacer({"A": "B", "B": "C"})
    res = replacer.replace("A and B")
    assert res == "B and C"


def test_safe_replacer_empty():
    """空文字・空辞書時の安全な動作検証。"""
    replacer = SafeReplacer({})
    assert replacer.replace("Hello") == "Hello"
