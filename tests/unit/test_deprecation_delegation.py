import pytest
import warnings
from unittest.mock import MagicMock
from src.backend.engine_context import ContextManager
from src.agents.context_builder_agent import ContextBuilderAgent

def test_context_manager_deprecation():
    """Step 69: ContextManagerが非推奨警告を出すか検証"""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        
        repo = MagicMock()
        cm = ContextManager(repo=repo)
        
        assert len(w) > 0
        assert any(issubclass(warning.category, DeprecationWarning) for warning in w)
        assert "ContextManager is deprecated" in str(w[-1].message)

def test_context_manager_delegation():
    """Step 69: ContextManagerがContextBuilderAgentに委譲するか検証"""
    repo = MagicMock()
    cm = ContextManager(repo=repo)
    
    # 委譲先が初期化されることを確認
    delegate = cm._get_delegate()
    assert isinstance(delegate, ContextBuilderAgent)
