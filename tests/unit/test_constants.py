from config import constants


def test_episode_constants():
    assert constants.EP_FINAL == 8
    assert constants.EP_CLIMAX == 7


def test_rate_limit_constants():
    assert constants.RATE_LIMIT_MAX_REQUESTS == 100
    assert constants.RATE_LIMIT_WINDOW_SECONDS == 60
    assert constants.RATE_LIMIT_STORE_MAX_ENTRIES == 10000


def test_timeout_constants():
    assert constants.DEFAULT_API_TIMEOUT_SEC == 120.0
    assert constants.LONG_RUNNING_TIMEOUT_SEC == 300.0
    assert constants.STREAM_TIMEOUT_SEC == 180.0


def test_constants_are_final():
    # Final アノテーションが付与されているため再代入は静的解析で検出されるが、
    # ここでは値が存在し期待通りであることを確認する。
    for name in (
        "EP_FINAL",
        "EP_CLIMAX",
        "RATE_LIMIT_MAX_REQUESTS",
        "RATE_LIMIT_WINDOW_SECONDS",
        "RATE_LIMIT_STORE_MAX_ENTRIES",
        "DEFAULT_API_TIMEOUT_SEC",
        "LONG_RUNNING_TIMEOUT_SEC",
        "STREAM_TIMEOUT_SEC",
    ):
        assert hasattr(constants, name)
