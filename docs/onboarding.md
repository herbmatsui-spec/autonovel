# Onboarding & Reference Guide

This document serves as the primary entry point for new developers joining the Hegemony Novel Engine project.

## 1. Project Glossary
To ensure consistent communication, use the following terminology:

| Term | Definition | Component |
| :--- | :--- | :--- |
| **Orchestrator** | Manages the overall app lifecycle, page routing, and initialization. | `app.py` |
| **State Keeper** | Ensures type-safe session management and disk persistence. | `state.py` |
| **Engine Mediator** | Simplifies complex engine logic into UI-friendly API calls. | `engine.py` / `EngineService` |
| **Plugin Hub** | Dynamically loads and manages optional logic extensions. | `plugin_loader.py` |
| **Reliability Agent** | Monitors system health and handles error boundaries. | `health_check.py` |
| **Narrative Agent** | LLM-driven specialized logic for specific writing tasks. | `src/agents/` |

## 2. Quick Start for Developers

### Environment Setup
1. **Install Dependencies**:
   ```bash
   # Use the project's preferred package manager (e.g., uv or pip)
   pip install -r requirements.txt
   ```
2. **Configure API Keys**:
   - You can input your Gemini API key directly in the sidebar of the running app.
3. **Run the Application**:
   ```bash
   streamlit run streamlit_app/app.py
   ```

### Project Layout at a Glance
- `streamlit_app/`: Everything related to the Frontend (UI, State, Proxy).
- `src/`: Core Backend logic (Services, Agents, Database).
- `config/`: Static configurations, prompt templates, and constants.
- `docs/`: Architecture records (ADR), guides, and sequences.
- `plugins/`: Dynamic extensions to the core logic.
- `storage/`: Local JSON files for session persistence.

## 3. FAQ

**Q: Why not use `st.session_state` directly?**
A: To avoid "State Spaghetti." Direct access leads to untyped data and hard-to-track mutations. `UIStateStore` provides a single point of truth and automatic persistence to disk.

**Q: How do I debug a background job?**
A: Check the `monitored_jobs` in the `UIStateStore`. Log messages for jobs are routed through the structured logging system; check `logs/server.log` for backend execution details.

**Q: Where should I put a new prompt template?**
A: Place them in `prompts/` or `config/data/`. If the prompt is part of a specialized agent, it should be integrated into the agent's prompt registry logic in `src/engine/prompts/`.

**Q: How does the plugin system work?**
A: The `PluginLoader` scans the `plugins/` directory at startup. Any `.py` file there is imported. If the module contains a `register()` function, it is executed to hook into the system.

---

## 4. Architecture Index
For deeper technical details, refer to the following ADRs:
- [ADR-001: State Management Architecture](docs/adr/001-state-management.md)
- [ADR-002: Plugin System Architecture](docs/adr/002-plugin-system.md)
- [ADR-003: Engine Mediator Architecture](docs/adr/003-engine-mediator.md)
