import pytest
import inspect
from src.domain.interfaces.hook_repository import HookRepository


def test_hook_repository_exists():
    """HookRepository クラスが存在することを確認"""
    assert HookRepository is not None


def test_hook_repository_has_add_method():
    """add メソッドが存在することを確認"""
    assert hasattr(HookRepository, 'add')
    assert callable(getattr(HookRepository, 'add'))
    
    # シグニチャを確認
    sig = inspect.signature(HookRepository.add)
    params = list(sig.parameters.keys())
    assert 'self' in params
    assert 'hook' in params


def test_hook_repository_has_get_by_book_id_method():
    """get_by_book_id メソッドが存在することを確認"""
    assert hasattr(HookRepository, 'get_by_book_id')
    assert callable(getattr(HookRepository, 'get_by_book_id'))
    
    # シグニチャを確認
    sig = inspect.signature(HookRepository.get_by_book_id)
    params = list(sig.parameters.keys())
    assert 'self' in params
    assert 'book_id' in params


def test_hook_repository_has_get_pending_hooks_method():
    """get_pending_hooks メソッドが存在することを確認"""
    assert hasattr(HookRepository, 'get_pending_hooks')
    assert callable(getattr(HookRepository, 'get_pending_hooks'))
    
    # シグニチャを確認
    sig = inspect.signature(HookRepository.get_pending_hooks)
    params = list(sig.parameters.keys())
    assert 'self' in params
    assert 'book_id' in params


def test_hook_repository_cannot_be_instantiated_directly():
    """直接インスタンス化できないことを確認（抽象クラスとしての振る舞い）"""
    # 今回は ABC を使っていないので、インスタンス化は可能だが、
    # メソッドを呼び出すと NotImplementedError が送出されることを確認
    repo = HookRepository()
    
    # add メソッドを呼び出すと NotImplementedError
    with pytest.raises(NotImplementedError):
        repo.add(None)
    
    # get_by_book_id メソッドを呼び出すと NotImplementedError
    with pytest.raises(NotImplementedError):
        repo.get_by_book_id(1)
    
    # get_pending_hooks メソッドを呼び出すと NotImplementedError
    with pytest.raises(NotImplementedError):
        repo.get_pending_hooks(1)