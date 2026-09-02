"""Gacha / Digest サービスの単体テスト (DB はモック)。

Step 40-46:
- db 必須化 (ValueError)
- ValueError → HTTP 400 (router 層は別テスト)
- generate_suggestions が LLM を呼ぶ
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.domain.entities.easy_mode import (
    DigestRequest,
    GachaRequest,
)


# ---------------------------------------------------------------------------
# Step 40: GachaService は db 必須
# ---------------------------------------------------------------------------


def test_gacha_service_requires_db():
    from src.services.gacha_service import GachaService

    with pytest.raises(ValueError, match="requires db"):
        GachaService(db=None)
    with pytest.raises(ValueError, match="requires db"):
        GachaService(llm_service=MagicMock(), db=None)


def test_gacha_service_accepts_db():
    from src.services.gacha_service import GachaService

    svc = GachaService(llm_service=MagicMock(), db=MagicMock())
    assert svc._db is not None


# ---------------------------------------------------------------------------
# Step 41: DigestService は db 必須
# ---------------------------------------------------------------------------


def test_digest_service_requires_db():
    from src.services.digest_service import DigestService

    with pytest.raises(ValueError, match="requires db"):
        DigestService(db=None)


def test_digest_service_accepts_db():
    from src.services.digest_service import DigestService

    svc = DigestService(llm_service=MagicMock(), db=MagicMock())
    assert svc._db is not None


# ---------------------------------------------------------------------------
# Step 42: gacha validate_value_error (router レベル)
# ---------------------------------------------------------------------------


def test_gacha_request_validation():
    """GachaRequest は genre/keywords 必須 (Pydantic バリデーション)。"""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        GachaRequest(genre="", keywords=[])


def test_digest_request_accepts_empty_strings():
    """DigestRequest は空文字でも受け入れる (router 層で 400 化される)。"""
    req = DigestRequest(request_id="", selected_plan_id="")
    assert req.request_id == ""


# ---------------------------------------------------------------------------
# Step 43: generate_suggestions が実 LLM 呼び出し
# ---------------------------------------------------------------------------


async def test_digest_suggestions_uses_llm():
    """generate_suggestions は LLM を呼び、結果をパースして返す。"""
    from src.services.digest_service import DigestService

    fake_llm = MagicMock()
    fake_llm.generate_text = AsyncMock(
        return_value="- 主人公の内面をもっと描写する\n- 伏線を 1 つ追加する\n- 設定を練る"
    )

    svc = DigestService(llm_service=fake_llm, db=MagicMock())
    res = await svc.generate_suggestions("テスト章本文です。")

    fake_llm.generate_text.assert_awaited_once()
    assert len(res) >= 1
    # 各要素に「- 」や「・」が付いていたら除去されている
    for line in res:
        assert not line.startswith("-")
        assert not line.startswith("・")


async def test_digest_suggestions_empty_chapter_falls_back():
    """空 chapter では LLM 呼ばず既定の提案を返す。"""
    from src.services.digest_service import DigestService

    fake_llm = MagicMock()
    fake_llm.generate_text = AsyncMock()

    svc = DigestService(llm_service=fake_llm, db=MagicMock())
    res = await svc.generate_suggestions("")

    fake_llm.generate_text.assert_not_awaited()
    assert res == ["続行: (空章のため先頭から再開)", "調査が必要な未確認な要素を指摘"]


async def test_digest_suggestions_llm_failure_falls_back():
    """LLM 例外時は固定文字列フォールバック。"""
    from src.services.digest_service import DigestService

    fake_llm = MagicMock()
    fake_llm.generate_text = AsyncMock(side_effect=RuntimeError("LLM down"))

    svc = DigestService(llm_service=fake_llm, db=MagicMock())
    res = await svc.generate_suggestions("なんらかの章本文")

    assert isinstance(res, list)
    assert len(res) >= 1


# ---------------------------------------------------------------------------
# Step 44: process_chapter は既存仕様のまま (章切り出し)
# ---------------------------------------------------------------------------


def test_process_chapter_truncates():
    from src.services.digest_service import process_chapter

    long = "あ" * 3000
    out = process_chapter(long)
    assert out.endswith("...")
    assert len(out) <= 1500 + 3  # 末尾 "..." 含む


def test_process_chapter_short_unchanged():
    from src.services.digest_service import process_chapter

    short = "短い章"
    assert process_chapter(short) == short


# ---------------------------------------------------------------------------
# Step 45-46: 既存 gacha / digest テストとの互換性
# ---------------------------------------------------------------------------


def test_gacha_service_module_no_in_memory_cache():
    """_GACHA_CACHE グローバルが削除された。"""
    import src.services.gacha_service as mod

    assert not hasattr(mod, "_GACHA_CACHE")


def test_digest_service_module_no_in_memory_store():
    """_BOOK_STORE グローバルが削除された。"""
    import src.services.digest_service as mod

    assert not hasattr(mod, "_BOOK_STORE")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
