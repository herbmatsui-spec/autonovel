import pytest
from src.backend.engine import UltimateHegemonyEngine
from src.infrastructure.repositories.foreshadowing_repository import InMemoryForeshadowingRepository
from src.infrastructure.repositories.hook_repository import InMemoryHookRepository


def test_engine_foreshadowing_repository_injection():
    """UltimateHegemonyEngine に foreshadowing_repository が正しく注入されることを確認"""
    # モックのリポジトリを作成
    mock_repo = InMemoryForeshadowingRepository()
    
    # エンジンを作成（他の依存関係はNoneでOK）
    engine = UltimateHegemonyEngine(
        api_key="test-key",
        foreshadowing_repository=mock_repo
    )
    
    # リポジトリが正しく設定されているか確認
    assert engine.foreshadowing_repository == mock_repo
    assert isinstance(engine.foreshadowing_repository, InMemoryForeshadowingRepository)


def test_engine_hook_repository_injection():
    """UltimateHegemonyEngine に hook_repository が正しく注入されることを確認"""
    # モックのリポジトリを作成
    mock_repo = InMemoryHookRepository()
    
    # エンジンを作成（他の依存関係はNoneでOK）
    engine = UltimateHegemonyEngine(
        api_key="test-key",
        hook_repository=mock_repo
    )
    
    # リポジトリが正しく設定されているか確認
    assert engine.hook_repository == mock_repo
    assert isinstance(engine.hook_repository, InMemoryHookRepository)


def test_engine_both_repositories_injection():
    """UltimateHegemonyEngine に両方のリポジトリが正しく注入されることを確認"""
    # モックのリポジトリを作成
    mock_foreshadowing_repo = InMemoryForeshadowingRepository()
    mock_hook_repo = InMemoryHookRepository()
    
    # エンジンを作成
    engine = UltimateHegemonyEngine(
        api_key="test-key",
        foreshadowing_repository=mock_foreshadowing_repo,
        hook_repository=mock_hook_repo
    )
    
    # 両方のリポジトリが正しく設定されているか確認
    assert engine.foreshadowing_repository == mock_foreshadowing_repo
    assert isinstance(engine.foreshadowing_repository, InMemoryForeshadowingRepository)
    assert engine.hook_repository == mock_hook_repo
    assert isinstance(engine.hook_repository, InMemoryHookRepository)


def test_engine_hook_repository_none_by_default():
    """デフォルトでは hook_repository が None であることを確認"""
    # エンジンを作成（hook_repository を指定しない）
    engine = UltimateHegemonyEngine(
        api_key="test-key"
        # hook_repository は指定しない
    )
    
    # デフォルトでは None であることを確認
    assert engine.hook_repository is None


def test_engine_other_dependencies_still_work():
    """他の依存関係が正常に動作することを確認"""
    # 基本的なエンジン作成が可能であることを確認
    engine = UltimateHegemonyEngine(
        api_key="test-key"
    )
    
    # 基本的な属性が設定されているか確認
    assert engine.api_key == "test-key"
    assert engine.repo is None
    assert engine.db is None
    assert engine.llm is None
    assert engine.cooldown is None
    assert engine.foreshadowing_repository is None  # 今回追加した項目のうち、指定しなかった方
    assert engine.hook_repository is None          # 今回追加した項目のうち、指定しなかった方
    assert engine._legacy == {}