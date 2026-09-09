"""
tests/unit/test_deprecation_delegation.py
Step 69: スプリットブレイン解消・互換アダプタの委譲テスト
"""
import pytest
import warnings
from unittest.mock import MagicMock, AsyncMock


def test_context_manager_deprecation_and_delegation():
    """Step 61, 62: ContextManager emits DeprecationWarning and creates delegate ContextBuilderAgent."""
    from src.backend.engine_context import ContextManager
    from src.agents.context_builder_agent import ContextBuilderAgent

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        mock_repo = MagicMock()
        cm = ContextManager(repo=mock_repo)
        
        # Verify DeprecationWarning
        assert any(issubclass(item.category, DeprecationWarning) for item in w)
        assert any("ContextManager is deprecated" in str(item.message) for item in w)
        
        # Verify delegate
        delegate = cm._get_delegate()
        assert delegate is not None
        assert isinstance(delegate, ContextBuilderAgent)


def test_context_builder_deprecation_and_alias():
    """Step 63: ContextBuilder emits DeprecationWarning and delegates to ContextBuilderAgent."""
    from src.agents.context_builder import ContextBuilder, ContextBuilderAgent

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        mock_agent = MagicMock()
        cb = ContextBuilder(agent=mock_agent)
        
        assert any(issubclass(item.category, DeprecationWarning) for item in w)
        assert any("ContextBuilder is deprecated" in str(item.message) for item in w)
        assert cb._delegate is not None
        assert isinstance(cb._delegate, ContextBuilderAgent)


def test_logical_auditor_deprecation():
    """Step 65: LogicalAuditor emits DeprecationWarning."""
    from src.agents.audit import LogicalAuditor

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        auditor = LogicalAuditor(repo=MagicMock(), llm=MagicMock())
        assert any(issubclass(item.category, DeprecationWarning) for item in w)
        assert any("LogicalAuditor is deprecated" in str(item.message) for item in w)


def test_audit_agent_alias_and_specialist_adapter():
    """Step 66, 68: AuditAgent has run_specialist_audit and AuditSkillAgent alias exists."""
    from src.agents.audit_agent import AuditAgent, AuditSkillAgent
    from src.agents.audit import AuditAgent as LegacyAuditAgent

    # Alias checks
    assert AuditSkillAgent is AuditAgent
    assert LegacyAuditAgent is AuditAgent

    # Instantiation and adapter method check
    agent = AuditAgent(repo=MagicMock(), llm=MagicMock())
    assert hasattr(agent, "run_specialist_audit")
    assert callable(agent.run_specialist_audit)
