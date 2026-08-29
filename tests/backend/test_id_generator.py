"""generate_prefixed_id の UUID 長テスト"""
from src.backend.utils.id_generator import generate_prefixed_id


def test_default_length_is_at_least_16():
    """UUID 切り詰め長 >= 16 で衝突確率を下げる"""
    tid = generate_prefixed_id("test")
    suffix = tid.split("_", 1)[1]
    assert len(suffix) >= 16, f"Expected >= 16 chars, got {len(suffix)}: {suffix}"


def test_explicit_length_works():
    tid = generate_prefixed_id("t", length=20)
    assert len(tid.split("_", 1)[1]) == 20


def test_uniqueness():
    """同一プレフィックスで複数生成しても一意"""
    ids = {generate_prefixed_id("uniq") for _ in range(100)}
    assert len(ids) == 100