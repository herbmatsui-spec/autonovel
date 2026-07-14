"""Step 48: Minimal end-to-end validation script.
This script performs import checks and basic instantiation of the key modules
required by streamlit_app/app.py.
"""
import importlib

MODULES = [
    "streamlit_app.app",
    "streamlit_app.engine_service",
    "streamlit_app.sidebar",
    "streamlit_app.state",
    "streamlit_app.landing",
    "streamlit_app.pages_config",
    "streamlit_app.event_bus",
    "streamlit_app.backend_launcher",
    "streamlit_app.progress",
    "streamlit_app.api_client",
    "src.health_check",
    "src.state",
    "src.sidebar",
    "src.landing",
    "src.pages_config",
    "src.ui_components",
    "src.ui_tabs_planning",
    "src.ui_tabs_writing",
    "src.ui_tabs_analytics",
    "src.ui_tabs_marketing",
    "src.ui_tabs_audit",
    "src.ui_tabs_monitor",
    "src.engine_service",
    "src.llm.gemini_client",
    "src.llm.model_router",
    "src.services.llm_service",
    "src.agents.base",
    "src.agents.writing",
    "src.agents.planning",
    "src.agents.bible",
    "src.agents.audit",
    "src.agents.marketing",
    "src.agents.state_validator",
    "src.agents.diversity_scorer",
    "src.services.writing_pipeline",
    "src.services.plot_service",
    "src.services.novel_service",
    "src.services.audit_service",
    "src.services.parallel_audit",
    "src.services.narrative_scoring_service",
    "src.services.content_processor",
    "src.services.healing_pipeline",
    "src.state_manager",
    "src.ui_utils",
    "src.progress",
    "src.proxy",
    "src.actions",
    "src.workflow_types",
    "src.core.plugin_loader",
    "src.core.observability",
]


def main() -> int:
    errors = []
    for module_name in MODULES:
        try:
            importlib.import_module(module_name)
        except Exception as exc:  # pragma: no cover - surfaced below
            errors.append(f"{module_name}: {exc}")

    if errors:
        print("IMPORT ERRORS:")
        for err in errors:
            print(err)
        return 1

    from src.engine_service import EngineService
    service = EngineService(api_key="test")
    assert service.engine is not None

    from src.agents.state_validator import StateValidatorAgent
    validator = StateValidatorAgent()
    issues = importlib.import_module("asyncio").run(validator.validate({"api_key": None, "app_mode": "easy"}))
    assert isinstance(issues, list)

    print("Step 48 validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

