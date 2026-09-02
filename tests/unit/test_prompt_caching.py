from unittest.mock import AsyncMock, patch

import pytest

from src.services.prompt_caching import PromptCacheManager, UnifiedPromptCache


def test_prompt_cache_manager_basic():
    """PromptCacheManager のキャッシュ管理とクリア動作の検証。"""
    mgr = PromptCacheManager()
    mgr._cache_map["key1"] = "mock_cached_content"

    assert mgr.get_or_create_cache("key1", [{"parts": ["test"]}]) == "mock_cached_content"

    mgr.clear_cache("key1")
    assert "key1" not in mgr._cache_map


@pytest.mark.asyncio
async def test_unified_prompt_cache_get_and_set():
    """UnifiedPromptCache のモックを用いた get/set 検証。"""
    cache = UnifiedPromptCache(l1_maxsize=10)

    mock_prompt_service = AsyncMock()
    mock_prompt_service.get.return_value = {"generated_text": "cached output"}
    mock_prompt_service.set.return_value = None

    with patch.object(cache, "_ensure_prompt_cache", return_value=mock_prompt_service):
        # キャッシュ保存
        await cache.cache_response(
            template_name="novel_writer",
            prompt="Write a chapter",
            response={"generated_text": "cached output"},
            model_id="gemini-flash",
        )
        assert mock_prompt_service.set.called

        # キャッシュ取得
        result = await cache.get_cached_response(
            template_name="novel_writer",
            prompt="Write a chapter",
            model_id="gemini-flash",
        )
        assert result == {"generated_text": "cached output"}
        assert mock_prompt_service.get.called
