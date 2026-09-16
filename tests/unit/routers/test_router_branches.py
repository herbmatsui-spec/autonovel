from src.backend.routers.branches import _compute_unified_diff, _compute_side_by_side_diff, _validate_uuid

def test_validate_uuid_valid():
    valid_uuid = "123e4567-e89b-12d3-a456-426614174000"
    assert _validate_uuid(valid_uuid) is True

def test_validate_uuid_invalid():
    assert _validate_uuid("not-a-uuid") is False
    assert _validate_uuid("") is False

def test_compute_unified_diff():
    text_a = "第1章 開始。\n彼は走った。\n終了。"
    text_b = "第1章 開始。\n彼はゆっくり歩いた。\n終了。"
    diff = _compute_unified_diff(text_a, text_b)
    assert "-彼は走った。" in diff
    assert "+彼はゆっくり歩いた。" in diff

def test_compute_side_by_side_diff():
    text_a = "リンゴ\nゴリラ"
    text_b = "リンゴ\nラッパ"
    diff_data = _compute_side_by_side_diff(text_a, text_b)
    assert isinstance(diff_data, list)
    assert len(diff_data) >= 2
