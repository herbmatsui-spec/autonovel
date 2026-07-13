
import pytest

from src.engine_service import EngineService


def test_engine_service_initialization():
    """EngineServiceが正しく初期化できるかテスト"""
    # モック用に空のAPIキーを使用
    service = EngineService(api_key="test-key")
    assert service is not None
    assert service.engine is not None

def test_get_instance_in_session():
    """Streamlitセッション経由でインスタンスが取得できるか"""
    # streamlitのセッション状態をモックする必要があるかもしれないが
    # ここでは基本的な構造の確認とする
    try:
        instance = EngineService.get_instance(api_key="test-key")
        assert instance is not None
    except Exception as e:
        pytest.fail(f"get_instance failed: {e}")
