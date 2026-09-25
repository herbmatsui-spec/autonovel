"""DIコンテナでの圧縮コンポーネント注入確認テスト"""
from __future__ import annotations

import pytest
from unittest.mock import Mock

from src.core.container.app import AppContainer
from src.services.compression.compressor import FourLayerCompressor
from src.services.compression.models import CompressionConfig
from src.agents.context_builder_agent import ContextBuilderAgent
from src.services.writing_service import WritingService


class TestCompressionDIInjection:
    """DIコンテナから圧縮コンポーネントが正しく注入されることの確認"""

    def test_compressor_provider_returns_four_layer_compressor(self):
        """AppContainer.compressor() が FourLayerCompressor インスタンスを返すこと"""
        container = AppContainer()
        compressor = container.compressor()
        assert isinstance(compressor, FourLayerCompressor)

    def test_compressor_is_singleton(self):
        """AppContainer.compressor() が同一インスタンスを返すこと（Singleton）"""
        container = AppContainer()
        compressor1 = container.compressor()
        compressor2 = container.compressor()
        assert compressor1 is compressor2

    def test_compression_config_provider_returns_compression_config(self):
        """AppContainer.compression_config() が CompressionConfig インスタンスを返すこと"""
        container = AppContainer()
        config = container.compression_config()
        assert isinstance(config, CompressionConfig)

    def test_context_builder_agent_receives_compressor(self):
        """AppContainer.context_builder_agent().compressor が同一インスタンスであること"""
        container = AppContainer()
        agent = container.context_builder_agent()
        compressor = container.compressor()
        assert agent.compressor is not None
        assert agent.compressor is compressor

    def test_writing_service_receives_compressor(self):
        """AppContainer.writing_service().compressor が同一インスタンスであること"""
        container = AppContainer()
        service = container.writing_service()
        compressor = container.compressor()
        assert service.compressor is not None
        assert service.compressor is compressor

    def test_compressor_config_injection(self):
        """CompressionConfig が正しく FourLayerCompressor に注入されること"""
        container = AppContainer()
        compressor = container.compressor()
        assert compressor.config is not None
        assert isinstance(compressor.config, CompressionConfig)

    def test_multiple_containers_independent(self):
        """異なるコンテナインスタンスは独立したシングルトンを持つこと"""
        container1 = AppContainer()
        container2 = AppContainer()
        comp1 = container1.compressor()
        comp2 = container2.compressor()
        assert comp1 is not comp2
        assert isinstance(comp1, FourLayerCompressor)
        assert isinstance(comp2, FourLayerCompressor)

    def test_compressor_layers_initialized(self):
        """FourLayerCompressor の各層が正しく初期化されていること"""
        container = AppContainer()
        compressor = container.compressor()
        assert compressor.layer1 is not None
        assert compressor.layer2 is not None
        assert compressor.layer3 is not None
        assert compressor.layer4 is not None
        assert compressor.cache is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])