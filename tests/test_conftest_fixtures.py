"""
tests/conftest.py の共有フィクスチャ整合性検証テスト (Step 3)
"""

import pytest


def test_conftest_environment_setup():
    """conftestによってテスト環境変数が正しく初期化されていること"""
    import os
    assert os.environ.get("APP_ENV") == "testing"
    assert os.environ.get("AUTONOVEL_RAG_MODE") == "memory"
    assert os.environ.get("AUTH_DISABLED") == "true"


def test_conftest_mock_llm_adapter_fixture(mock_llm_adapter, llm_mocker):
    """mock_llm_adapter および llm_mocker フィクスチャが正常に動作すること"""
    assert mock_llm_adapter is not None
    assert llm_mocker is not None
    # get_llm_adapter がモックを返すこと
    from src.services.llm.factory import get_llm_adapter
    adapter = get_llm_adapter("test-model")
    assert adapter is mock_llm_adapter
