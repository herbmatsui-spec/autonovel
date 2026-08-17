"""
<<<<<<< ours
Unit tests for UltimateHegemonyEngine new constructor with EngineDeps.
=======
Unit tests for UltimateHegemonyEngine new constructor.
>>>>>>> theirs
"""

import warnings
from unittest.mock import MagicMock

import pytest

from src.backend.engine import UltimateHegemonyEngine
<<<<<<< ours
from src.backend.engine_deps import EngineDeps
=======
>>>>>>> theirs


class TestEngineConstructor:
    """Test the new explicit constructor of UltimateHegemonyEngine."""

    def test_new_constructor_with_all_dependencies(self):
        mock_repo = MagicMock()
        mock_db = MagicMock()
        mock_llm = MagicMock()
        mock_cooldown = MagicMock()
        mock_plot_service = MagicMock()
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

<<<<<<< ours
        deps = EngineDeps(
=======
        engine = UltimateHegemonyEngine(
            api_key="test-key",
            repo=mock_repo,
            db=mock_db,
            llm=mock_llm,
            cooldown=mock_cooldown,
            plot_service=mock_plot_service,
>>>>>>> theirs
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

<<<<<<< ours
        engine = UltimateHegemonyEngine(
            api_key="test-key",
            repo=mock_repo,
            db=mock_db,
            llm=mock_llm,
            cooldown=mock_cooldown,
            plot_service=mock_plot_service,
            deps=deps,
        )

=======
>>>>>>> theirs
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

    def test_new_constructor_with_none_dependencies_fallbacks_to_legacy(self):
        """Test that None explicit dependencies fall back to _legacy dict."""
        mock_repo = MagicMock()
        mock_db = MagicMock()
        mock_llm = MagicMock()
        mock_cooldown = MagicMock()
        mock_plot_service = MagicMock()
        mock_planner = MagicMock()
        mock_writer = MagicMock()

<<<<<<< ours
        # Create engine with EngineDeps having some None values
        deps = EngineDeps(
=======
        # Create engine with explicit None for some params
        engine = UltimateHegemonyEngine(
            api_key="test-key",
            repo=mock_repo,
            db=mock_db,
            llm=mock_llm,
            cooldown=mock_cooldown,
            plot_service=mock_plot_service,
>>>>>>> theirs
            planner=mock_planner,
            writer=mock_writer,
            pm=None,
            ctx_mgr=None,
            formatter=None,
            validator=None,
            auditor=None,
            narrative=None,
            critique=None,
            marketing=None,
            bible_agent=None,
            plot_agent=None,
            style_rag=None,
        )

<<<<<<< ours
        # Pass legacy deps via **legacy (simulating legacy caller)
        engine = UltimateHegemonyEngine(
            api_key="test-key",
            repo=mock_repo,
            db=mock_db,
            llm=mock_llm,
            cooldown=mock_cooldown,
            plot_service=mock_plot_service,
            deps=deps,
            pm="legacy-pm",
            ctx_mgr="legacy-ctx_mgr",
            formatter="legacy-formatter",
            validator="legacy-validator",
            auditor="legacy-auditor",
            narrative="legacy-narrative",
            critique="legacy-critique",
            marketing="legacy-marketing",
            bible_agent="legacy-bible_agent",
            plot_agent="legacy-plot_agent",
            style_rag="legacy-style_rag",
        )
=======
        # Manually populate _legacy (simulating legacy caller)
        engine._legacy = {
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
>>>>>>> theirs

        # Explicit ones should be returned directly
        assert engine.planner is mock_planner
        assert engine.writer is mock_writer

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
<<<<<<< ours
        """Test that _legacy_dep raises AttributeError for missing keys."""
        # Provide all required deps via EngineDeps to pass validation
        deps = EngineDeps(
            planner=MagicMock(),
            writer=MagicMock(),
            pm=MagicMock(),
            ctx_mgr=MagicMock(),
            formatter=MagicMock(),
            validator=MagicMock(),
            auditor=MagicMock(),
            narrative=MagicMock(),
            critique=MagicMock(),
            marketing=MagicMock(),
            bible_agent=MagicMock(),
            plot_agent=MagicMock(),
            style_rag=MagicMock(),
        )
        engine = UltimateHegemonyEngine(
            api_key="test-key",
            deps=deps,
        )
=======
        engine = UltimateHegemonyEngine(api_key="test-key")
>>>>>>> theirs

        with pytest.raises(AttributeError) as exc_info:
            engine._legacy_dep("nonexistent")

        assert "nonexistent" in str(exc_info.value)

    def test_deprecation_warning_on_legacy_access(self):
<<<<<<< ours
        engine = UltimateHegemonyEngine(
            api_key="test-key",
            planner=MagicMock(),
            writer=MagicMock(),
            ctx_mgr=MagicMock(),
            formatter=MagicMock(),
            validator=MagicMock(),
            auditor=MagicMock(),
            narrative=MagicMock(),
            critique=MagicMock(),
            marketing=MagicMock(),
            bible_agent=MagicMock(),
            plot_agent=MagicMock(),
            style_rag=MagicMock(),
            **{"pm": "legacy-pm"},
        )
=======
        engine = UltimateHegemonyEngine(api_key="test-key", pm=None)
        engine._legacy = {"pm": "legacy-pm"}
>>>>>>> theirs

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            _ = engine.pm  # This should trigger _legacy_dep

            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "_legacy_dep('pm')" in str(w[0].message)

    def test_ai_api_and_llm_client_removed(self):
        """Test that deprecated ai_api and llm_client properties are removed."""
        mock_llm = MagicMock()
<<<<<<< ours

        deps = EngineDeps(
            planner=MagicMock(),
            writer=MagicMock(),
            pm=MagicMock(),
            ctx_mgr=MagicMock(),
            formatter=MagicMock(),
            validator=MagicMock(),
            auditor=MagicMock(),
            narrative=MagicMock(),
            critique=MagicMock(),
            marketing=MagicMock(),
            bible_agent=MagicMock(),
            plot_agent=MagicMock(),
            style_rag=MagicMock(),
        )

        engine = UltimateHegemonyEngine(
            api_key="test-key",
            llm=mock_llm,
            deps=deps,
        )
=======
        engine = UltimateHegemonyEngine(api_key="test-key", llm=mock_llm)
>>>>>>> theirs

        # These properties should no longer exist
        assert not hasattr(engine, 'ai_api')
        assert not hasattr(engine, 'llm_client')
<<<<<<< ours

=======
        
>>>>>>> theirs
        # llm should still be accessible
        assert engine.llm is mock_llm

    def test_generate_json_property(self):
        mock_llm = MagicMock()
        mock_llm.generate_json = "test-generate-json"
<<<<<<< ours

        deps = EngineDeps(
            planner=MagicMock(),
            writer=MagicMock(),
            pm=MagicMock(),
            ctx_mgr=MagicMock(),
            formatter=MagicMock(),
            validator=MagicMock(),
            auditor=MagicMock(),
            narrative=MagicMock(),
            critique=MagicMock(),
            marketing=MagicMock(),
            bible_agent=MagicMock(),
            plot_agent=MagicMock(),
            style_rag=MagicMock(),
        )

        engine = UltimateHegemonyEngine(
            api_key="test-key",
            llm=mock_llm,
            deps=deps,
        )
=======
        engine = UltimateHegemonyEngine(api_key="test-key", llm=mock_llm)
>>>>>>> theirs

        assert engine.generate_json == "test-generate-json"

    def test_dispose_method(self):
        mock_db = MagicMock()
        mock_db.engine = MagicMock()
<<<<<<< ours

        deps = EngineDeps(
            planner=MagicMock(),
            writer=MagicMock(),
            pm=MagicMock(),
            ctx_mgr=MagicMock(),
            formatter=MagicMock(),
            validator=MagicMock(),
            auditor=MagicMock(),
            narrative=MagicMock(),
            critique=MagicMock(),
            marketing=MagicMock(),
            bible_agent=MagicMock(),
            plot_agent=MagicMock(),
            style_rag=MagicMock(),
        )

        engine = UltimateHegemonyEngine(
            api_key="test-key",
            db=mock_db,
            deps=deps,
        )
=======
        engine = UltimateHegemonyEngine(api_key="test-key", db=mock_db)
>>>>>>> theirs

        engine.dispose()

        mock_db.engine.dispose.assert_called_once()

    def test_dispose_method_no_engine_attribute(self):
        mock_db = MagicMock()
        del mock_db.engine  # Remove engine attribute
<<<<<<< ours

        deps = EngineDeps(
            planner=MagicMock(),
            writer=MagicMock(),
            pm=MagicMock(),
            ctx_mgr=MagicMock(),
            formatter=MagicMock(),
            validator=MagicMock(),
            auditor=MagicMock(),
            narrative=MagicMock(),
            critique=MagicMock(),
            marketing=MagicMock(),
            bible_agent=MagicMock(),
            plot_agent=MagicMock(),
            style_rag=MagicMock(),
        )

        engine = UltimateHegemonyEngine(
            api_key="test-key",
            db=mock_db,
            deps=deps,
        )
=======
        engine = UltimateHegemonyEngine(api_key="test-key", db=mock_db)
>>>>>>> theirs

        # Should not raise
        engine.dispose()

<<<<<<< ours
    def test_validate_dependencies_passes_with_deps(self):
        """Test that validate_dependencies passes when all deps provided via EngineDeps."""
        mock_repo = MagicMock()
        mock_db = MagicMock()
        mock_llm = MagicMock()
        mock_cooldown = MagicMock()
        mock_plot_service = MagicMock()

        deps = EngineDeps(
            planner=MagicMock(),
            writer=MagicMock(),
            pm=MagicMock(),
            ctx_mgr=MagicMock(),
            formatter=MagicMock(),
            validator=MagicMock(),
            auditor=MagicMock(),
            narrative=MagicMock(),
            critique=MagicMock(),
            marketing=MagicMock(),
            bible_agent=MagicMock(),
            plot_agent=MagicMock(),
            style_rag=MagicMock(),
        )

        # Should not raise
        engine = UltimateHegemonyEngine(
            api_key="test-key",
            repo=mock_repo,
            db=mock_db,
            llm=mock_llm,
            cooldown=mock_cooldown,
            plot_service=mock_plot_service,
            deps=deps,
        )

    def test_validate_dependencies_raises_when_missing(self):
        """Test that validate_dependencies raises when required deps missing."""
        mock_repo = MagicMock()
        mock_db = MagicMock()
        mock_llm = MagicMock()
        mock_cooldown = MagicMock()
        mock_plot_service = MagicMock()

        # Provide only some deps
        deps = EngineDeps(
            planner=MagicMock(),
            writer=MagicMock(),
            # pm, ctx_mgr, etc. are None
        )

        with pytest.raises(RuntimeError) as exc_info:
            UltimateHegemonyEngine(
                api_key="test-key",
                repo=mock_repo,
                db=mock_db,
                llm=mock_llm,
                cooldown=mock_cooldown,
                plot_service=mock_plot_service,
                deps=deps,
            )

        assert "Missing required dependencies" in str(exc_info.value)
        assert "pm" in str(exc_info.value)

=======
>>>>>>> theirs

class TestEngineContainerIntegration:
    """Test engine creation via DI container."""

    def test_container_creates_engine_with_all_dependencies(self):
        from src.core.container import AppContainer

        container = AppContainer()
        engine = container.engine()

        assert isinstance(engine, UltimateHegemonyEngine)
        assert engine.api_key == "DUMMY"
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
