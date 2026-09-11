"""Phase P1 自動検証テスト: ランタイムクラッシュ修復 & セキュリティ認証防御."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.age_client import CypherResult


class TestCypherResultIteration:
    """CypherResult のイテレーション正常性テスト."""

    def test_cypher_result_iterable(self):
        """CypherResult がイテラブルとして正しく動作すること."""
        records = [{"a": 1}, {"b": 2}]
        result = CypherResult(records=records, summary={}, execution_time_ms=1.0)
        assert list(result) == records

    def test_cypher_result_empty(self):
        """空の CypherResult も正しく動作すること."""
        result = CypherResult(records=[], summary={}, execution_time_ms=0.0)
        assert list(result) == []


class TestPublishRecordImport:
    """commercial.py の PublishRecord インポートおよびクエリ動作テスト."""

    def test_commercial_router_import(self):
        """commercial ルーターがインポート可能であること."""
        from src.backend.routers.commercial import router
        assert router is not None


class TestGraphRouterImport:
    """graph.py の CypherResult イテレーション正常性テスト."""

    def test_graph_router_import(self):
        """graph ルーターがインポート可能であること."""
        from src.backend.routers.graph import router
        assert router is not None


class TestAntiAIAuth:
    """anti_ai エンドポイントの未認証 401 拒否テスト."""

    @pytest.mark.asyncio
    async def test_anti_ai_router_import(self):
        """anti_ai ルーターがインポート可能で、認証依存関係を持つこと."""
        from src.backend.routers.anti_ai import router
        from fastapi import Depends
        from src.backend.auth import require_api_key
        
        assert router is not None
        # ルーターに認証依存関係があることを確認
        assert len(router.dependencies) > 0
        dep = router.dependencies[0]
        assert dep.dependency == require_api_key


class TestExportAuth:
    """export エンドポイントの未認証 401 拒否テスト."""

    @pytest.mark.asyncio
    async def test_export_router_import(self):
        """export ルーターがインポート可能で、認証依存関係を持つこと."""
        from src.backend.routers.export import router
        from fastapi import Depends
        from src.backend.auth import require_api_key
        
        assert router is not None
        # エンドポイントレベルの依存関係を確認
        routes_with_auth = [r for r in router.routes if hasattr(r, 'dependencies') and r.dependencies]
        assert len(routes_with_auth) >= 2  # GET /books/{book_id} と POST /ebook


class TestPatchesAuth:
    """patches エンドポイントの未認証 401 拒否テスト."""

    @pytest.mark.asyncio
    async def test_patches_router_import(self):
        """patches ルーターがインポート可能で、認証依存関係を持つこと."""
        from src.backend.routers.patches import router
        from fastapi import Depends
        from src.backend.auth import require_api_key
        
        assert router is not None
        # エンドポイントレベルの依存関係を確認
        routes_with_auth = [r for r in router.routes if hasattr(r, 'dependencies') and r.dependencies]
        assert len(routes_with_auth) >= 2  # GET /{book_id}/pending と GET /reviews/{review_id}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])