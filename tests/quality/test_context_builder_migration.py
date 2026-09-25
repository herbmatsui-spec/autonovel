"""
Regression tests for ContextBuilderAgent migration and ContextManager deprecation.
Verifies that ContextBuilderAgent fulfills all required context-building capabilities
and that ContextManager cleanly acts as a deprecation shim without dual-maintenance issues.
"""

from unittest.mock import AsyncMock, MagicMock
import warnings
import pytest

from src.agents.context_builder_agent import ContextBuilderAgent
from src.backend.engine_context import ContextManager


def test_context_builder_agent_interface():
    """Verify that ContextBuilderAgent has all essential context generation methods."""
    agent = ContextBuilderAgent.__new__(ContextBuilderAgent)
    assert hasattr(agent, "build_context")
    assert hasattr(agent, "execute")
    assert hasattr(agent, "_build_full_writing_context_internal")
    assert hasattr(agent, "_build_char_static_ctx")


def test_context_manager_issues_deprecation_warning():
    """Instantiating ContextManager must issue a DeprecationWarning."""
    mock_repo = MagicMock()
    with pytest.deprecated_call(match="ContextManager is deprecated"):
        cm = ContextManager(repo=mock_repo)
    assert cm.repo is mock_repo


def test_context_manager_delegation_to_agent():
    """ContextManager must lazily initialize or delegate to ContextBuilderAgent."""
    mock_repo = MagicMock()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        cm = ContextManager(repo=mock_repo)
        delegate = cm._get_delegate()
        assert delegate is not None
        assert isinstance(delegate, ContextBuilderAgent)


def test_app_container_context_provider():
    """AppContainer should resolve ctx_mgr without errors."""
    from src.core.container.app import AppContainer
    container = AppContainer()
    container.init_resources()
    assert container.ctx_mgr is not None
