"""PromptCacheService.invalidate_task_type のパターン一致テスト"""
import pytest
from unittest.mock import AsyncMock

from src.services.redis_cache import PromptCacheService


@pytest.mark.asyncio
async def test_invalidate_task_type_pattern_matches_real_key():
    """
    実キー: prompt:{template}:{model}:{version}:{task_type}:{hash[:16]}
    パターン: prompt:*:*:*:{task_type}:* （6要素中5番目がtask_type）
    """
    redis = AsyncMock()
    redis.invalidate_pattern = AsyncMock(return_value=5)
    svc = PromptCacheService(redis_cache=redis)

    # 呼び出されたパターンを捕捉
    captured = {}

    async def capture(pattern):
        captured["pattern"] = pattern
        return 5

    redis.invalidate_pattern = capture

    result = await svc.invalidate_task_type("generation")

    assert result == 5
    # 期待パターン: prompt:*:*:*:generation:*
    # 現在のバグ実装: "prompt:*:*:*:*:generation:*" なので 7 セクションになり不一致
    assert captured["pattern"] == "prompt:*:*:*:generation:*"


@pytest.mark.asyncio
async def test_invalidate_task_type_l1_cleanup():
    """L1キャッシュも正しくクリーンアップされること"""
    redis = AsyncMock()
    redis.invalidate_pattern = AsyncMock(return_value=3)

    # L1キャッシュをモック
    class MockL1:
        def __init__(self):
            self.data = {
                "prompt:tpl:model:1.0:generation:abc123:genre:0.7": "val1",
                "prompt:tpl:model:1.0:polishing:def456:genre:0.7": "val2",
                "other:key": "val3",
            }

        def keys(self):
            return list(self.data.keys())

        def __delitem__(self, key):
            del self.data[key]

        def __contains__(self, key):
            return key in self.data

    l1 = MockL1()
    svc = PromptCacheService(redis_cache=redis, l1_cache=l1)

    result = await svc.invalidate_task_type("generation")

    assert result == 3
    # generation タイプのキーのみ削除される
    assert "prompt:tpl:model:1.0:generation:abc123:genre:0.7" not in l1.data
    assert "prompt:tpl:model:1.0:polishing:def456:genre:0.7" in l1.data
    assert "other:key" in l1.data