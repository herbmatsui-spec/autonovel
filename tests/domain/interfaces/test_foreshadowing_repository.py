import pytest
import inspect
from src.domain.interfaces.foreshadowing_repository import ForeshadowingRepository


def test_foreshadowing_repository_exists():
    """ForeshadowingRepository クラスが存在することを確認"""
    assert ForeshadowingRepository is not None


def test_foreshadowing_repository_has_add_method():
    """add メソッドが存在することを確認"""
    assert hasattr(ForeshadowingRepository, 'add')
    assert callable(getattr(ForeshadowingRepository, 'add'))
    
    # シグニチャを確認
    sig = inspect.signature(ForeshadowingRepository.add)
    params = list(sig.parameters.keys())
    assert 'self' in params
    assert 'foreshadowing' in params


def test_foreshadowing_repository_has_get_by_book_id_method():
    """get_by_book_id メソッドが存在することを確認"""
    assert hasattr(ForeshadowingRepository, 'get_by_book_id')
    assert callable(getattr(ForeshadowingRepository, 'get_by_book_id'))
    
    # シグニチャを確認
    sig = inspect.signature(ForeshadowingRepository.get_by_book_id)
    params = list(sig.parameters.keys())
    assert 'self' in params
    assert 'book_id' in params


def test_foreshadowing_repository_has_get_unresolved_method():
    """get_unresolved メソッドが存在することを確認"""
    assert hasattr(ForeshadowingRepository, 'get_unresolved')
    assert callable(getattr(ForeshadowingRepository, 'get_unresolved'))
    
    # シグニチャを確認
    sig = inspect.signature(ForeshadowingRepository.get_unresolved)
    params = list(sig.parameters.keys())
    assert 'self' in params
    assert 'book_id' in params


def test_foreshadowing_repository_has_resolve_method():
    """resolve メソッドが存在することを確認"""
    assert hasattr(ForeshadowingRepository, 'resolve')
    assert callable(getattr(ForeshadowingRepository, 'resolve'))
    
    # シグニチャを確認
    sig = inspect.signature(ForeshadowingRepository.resolve)
    params = list(sig.parameters.keys())
    assert 'self' in params
    assert 'foreshadowing_id' in params
    assert 'volume' in params
    assert 'episode' in params


def test_foreshadowing_repository_has_get_balance_method():
    """get_balance メソッドが存在することを確認"""
    assert hasattr(ForeshadowingRepository, 'get_balance')
    assert callable(getattr(ForeshadowingRepository, 'get_balance'))
    
    # シグニチャを確認
    sig = inspect.signature(ForeshadowingRepository.get_balance)
    params = list(sig.parameters.keys())
    assert 'self' in params
    assert 'volume' in params


def test_foreshadowing_repository_cannot_be_instantiated_directly():
    """直接インスタンス化できないことを確認（抽象クラスとしての振る舞い）"""
    # 今回は ABC を使っていないので、インスタンス化は可能だが、
    # メソッドを呼び出すと NotImplementedError が送出されることを確認
    repo = ForeshadowingRepository()
    
    # add メソッドを呼び出すと NotImplementedError
    with pytest.raises(NotImplementedError):
        repo.add(None)
    
    # get_by_book_id メソッドを呼び出すと NotImplementedError
    with pytest.raises(NotImplementedError):
        repo.get_by_book_id(1)
    
    # get_unresolved メソッドを呼び出すと NotImplementedError
    with pytest.raises(NotImplementedError):
        repo.get_unresolved(1)
    
    # resolve メソッドを呼び出すと NotImplementedError
    with pytest.raises(NotImplementedError):
        repo.resolve("test", 1, 1)
    
    # get_balance メソッドを呼び出すと NotImplementedError
    with pytest.raises(NotImplementedError):
        repo.get_balance(1)