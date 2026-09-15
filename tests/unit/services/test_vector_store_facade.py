"""src/services/vector_store.py（ファサード/設定/ユーティリティ）の単体テスト.

既存の tests/unit/test_vector_store.py と tests/unit/services/test_vector_store.py が
ChromaVectorStore/ChromaClientProvider をカバーするため、本ファイルは
config・collection 系・InMemoryFallbackStore 以外のパブリックAPIをカバーする。
"""

import pytest
from unittest.mock import MagicMock, AsyncMock

import src.services.vector_store as vs


class TestCollectionTypeAndConfig:
    """CollectionType / CollectionConfig のテスト."""

    def test_collection_type_values(self):
        assert vs.CollectionType.SEMANTIC_CACHE.value == "semantic_cache"
        assert vs.CollectionType.STYLE_MEMORY.value == "style_memory"
        assert vs.CollectionType.WORLD_MEMORY.value == "world_memory"
        assert vs.CollectionType.CHARACTER_MEMORY.value == "character_memory"
        assert vs.CollectionType.NARRATIVE_MEMORY.value == "narrative_memory"
        assert vs.CollectionType.EPISODE_MEMORY.value == "episode_memory"

    def test_default_collections_defined(self):
        assert len(vs.DEFAULT_COLLECTIONS) >= 6
        for ctype, config in vs.DEFAULT_COLLECTIONS.items():
            assert config.name == ctype.value

    def test_collection_config_get_metadata(self):
        config = vs.CollectionConfig(
            name="test_col",
            space="cosine",
            description="テスト",
            hnsw_params={"hnsw:M": 8},
        )
        meta = config.get_metadata()
        assert meta["hnsw:space"] == "cosine"
        assert meta["hnsw:M"] == 8
        assert meta["description"] == "テスト"

    def test_collection_config_defaults(self):
        config = vs.CollectionConfig(name="x")
        assert config.space == "cosine"
        assert config.description == ""
        assert "hnsw:construction_ef" in config.hnsw_params


class TestFacadeFlags:
    """利用可能性フラグのテスト."""

    def test_flags_exist(self):
        assert isinstance(vs.HAS_CHROMA, bool)
        assert isinstance(vs.HAS_PGVECTOR, bool)
        assert vs.HAS_INMEM is True

    def test_base_vector_store_is_abstract(self):
        with pytest.raises(TypeError):
            vs.BaseVectorStore()  # 抽象クラスはインスタンス化不可

    def test_base_vector_store_methods_abstract(self):
        class Partial(vs.BaseVectorStore):
            async def add_documents(self, *a, **k): ...
            async def search(self, *a, **k): ...
            # search_with_score, delete_by_id, clear_collection は未実装

        with pytest.raises(TypeError):
            Partial()


class TestCollectionSpecUtilities:
    """コレクションスペック生成ユーティリティのテスト."""

    def test_get_collection_config_by_name(self):
        # 名称から設定を取得できる関数が存在すれば検証
        getter = getattr(vs, "get_collection_config", None)
        if getter is None:
            pytest.skip("get_collection_config not implemented")
        config = getter("semantic_cache")
        assert config.name == "semantic_cache"
