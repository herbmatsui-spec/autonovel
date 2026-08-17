"""
Unit tests for UltimateHegemonyEngine new constructor.
"""

import warnings
from unittest.mock import MagicMock

import pytest

from src.backend.engine import UltimateHegemonyEngine


def create_mock_engine(**overrides):
    """Create an engine with all required dependencies mocked."""
    mocks = {
        'planner': MagicMock(),
        'writer': MagicMock(),
        'pm': MagicMock(),
        'ctx_mgr': MagicMock(),
        'formatter': MagicMock(),
        'validator': MagicMock(),
        'auditor': MagicMock(),
        'narrative': MagicMock(),
        'critique': MagicMock(),
        'marketing': MagicMock(),
        'bible_agent': MagicMock(),
        'plot_agent': MagicMock(),
        'style_rag': MagicMock(),
    }
    mocks.update(overrides)
    
    return UltimateHegemonyEngine(
        api_key="test-key",
        **mocks
    )


class TestEngineConstructor:
    """Test the new explicit constructor of UltimateHegemonyEngine."""

    def test_new_constructor_with_all_dependencies(self):
        mock_planner = MagicMock()
        mock_writer = MagicMock()
        mock_pm = MagicMock()
        mock_ctx_mgr = MagicMock()
        mock_formatter = MagicMock()
        mock_validator = MagicMock()
        mock_auditor = MagicMock()
        mock_narrative = MagicMock()
        mock_critique = MagicMock()
        mock_marketing = MagicMock()
        mock_bible_agent = MagicMock()
        mock_plot_agent = MagicMock()
        mock_style_rag = MagicMock()

        engine = UltimateHegemonyEngine(
            api_key="test-key",
            planner=mock_planner,
            writer=mock_writer,
            pm=mock_pm,
            ctx_mgr=mock_ctx_mgr,
            formatter=mock_formatter,
            validator=mock_validator,
            auditor=mock_auditor,
            narrative=mock_narrative,
            critique=mock_critique,
            marketing=mock_marketing,
            bible_agent=mock_bible_agent,
            plot_agent=mock_plot_agent,
            style_rag=mock_style_rag,
        )

        assert engine.api_key == "test-key"
        assert engine.planner is mock_planner
        assert engine.writer is mock_writer
        assert engine.pm is mock_pm
        assert engine.ctx_mgr is mock_ctx_mgr
        assert engine.formatter is mock_formatter
        assert engine.validator is mock_validator
        assert engine.auditor is mock_auditor
        assert engine.narrative is mock_narrative
        assert engine.critique is mock_critique
        assert engine.marketing is mock_marketing
        assert engine.bible_agent is mock_bible_agent
        assert engine.plot_agent is mock_plot_agent
        assert engine.style_rag is mock_style_rag
        assert engine.planning_agent is mock_planner
        assert engine.logic_validator is mock_validator

    def test_legacy_fallback_when_explicit_is_none(self):
        """Test that explicit None dependencies fall back to _legacy dict."""
        # Create engine with all deps first
        engine = create_mock_engine()

        # Now replace some explicit deps with None and populate _legacy
        engine._pm = None
        engine._ctx_mgr = None
        engine._formatter = None
        engine._validator = None
        engine._auditor = None
        engine._narrative = None
        engine._critique = None
        engine._marketing = None
        engine._bible_agent = None
        engine._plot_agent = None
        engine._style_rag = None

        legacy_deps = {
            "pm": "legacy-pm",
            "ctx_mgr": "legacy-ctx_mgr",
            "formatter": "legacy-formatter",
            "validator": "legacy-validator",
            "auditor": "legacy-auditor",
            "narrative": "legacy-narrative",
            "critique": "legacy-critique",
            "marketing": "legacy-marketing",
            "bible_agent": "legacy-bible_agent",
            "plot_agent": "legacy-plot_agent",
            "style_rag": "legacy-style_rag",
        }
        engine._legacy = legacy_deps

        # Explicit ones (planner, writer) should still be returned directly
        assert engine.planner is not None
        assert engine.writer is not None

        # None ones should fall back to _legacy
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            assert engine.pm == "legacy-pm"
            assert engine.ctx_mgr == "legacy-ctx_mgr"
            assert engine.formatter == "legacy-formatter"
            assert engine.validator == "legacy-validator"
            assert engine.auditor == "legacy-auditor"
            assert engine.narrative == "legacy-narrative"
            assert engine.critique == "legacy-critique"
            assert engine.marketing == "legacy-marketing"
            assert engine.bible_agent == "legacy-bible_agent"
            assert engine.plot_agent == "legacy-plot_agent"
            assert engine.style_rag == "legacy-style_rag"

            # Should have emitted DeprecationWarning for each legacy access
            assert len(w) == 11
            for warning in w:
                assert issubclass(warning.category, DeprecationWarning)
                assert "_legacy_dep" in str(warning.message)

    def test_legacy_dep_raises_for_missing_key(self):
        engine = create_mock_engine()

        with pytest.raises(AttributeError) as exc_info:
            engine._legacy_dep("nonexistent")

        assert "nonexistent" in str(exc_info.value)

    def test_deprecation_warning_on_legacy_access(self):
        # Create engine with all deps, then set pm to None and populate _legacy
        engine = create_mock_engine()
        engine._pm = None
        engine._legacy = {"pm": "legacy-pm"}

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            _ = engine.pm  # This should trigger _legacy_dep

            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "_legacy_dep('pm')" in str(w[0].message)

    def test_ai_api_and_llm_client_removed(self):
        """Test that deprecated ai_api and llm_client properties are removed."""
        mock_llm = MagicMock()
        engine = create_mock_engine(llm=mock_llm)

        # These properties should no longer exist
        assert not hasattr(engine, 'ai_api')
        assert not hasattr(engine, 'llm_client')

        # llm should still be accessible
        assert engine.llm is mock_llm

    def test_generate_json_property(self):
        mock_llm = MagicMock()
        mock_llm.generate_json = "test-generate-json"
        engine = create_mock_engine(llm=mock_llm)

        assert engine.generate_json == "test-generate-json"

    def test_dispose_method(self):
        mock_db = MagicMock()
        mock_db.engine = MagicMock()
        engine = create_mock_engine(db=mock_db)

        engine.dispose()

        mock_db.engine.dispose.assert_called_once()

    def test_dispose_method_no_engine_attribute(self):
        mock_db = MagicMock()
        del mock_db.engine  # Remove engine attribute
        engine = create_mock_engine(db=mock_db)

        # Should not raise
        engine.dispose()


class TestEngineContainerIntegration:
    """Test engine creation via DI container."""

    def test_container_creates_engine_with_all_dependencies(self):
        import os
        os.environ.setdefault("GEMINI_API_KEY", "test-key-for-dev")
        
        from src.core.container import AppContainer

        container = AppContainer()
        engine = container.engine()

        assert isinstance(engine, UltimateHegemonyEngine)
        assert engine.api_key == "test-key-for-dev"
        assert engine.repo is not None
        assert engine.db is not None
        assert engine.llm is not None
        assert engine.cooldown is not None
        assert engine.plot_service is not None

        assert engine.planner is not None
        assert engine.writer is not None
        assert engine.pm is not None
        assert engine.ctx_mgr is not None
        assert engine.formatter is not None
        assert engine.validator is not None
        assert engine.auditor is not None
        assert engine.narrative is not None
        assert engine.critique is not None
        assert engine.marketing is not None
        assert engine.bible_agent is not None
        assert engine.plot_agent is not None
        assert engine.style_rag is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
