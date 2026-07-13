# UI Dependency Map (Phase 1, Step 1)

## 1. Architecture Overview
The current UI is built with Streamlit, following a Page-based structure with fragmented updates.

### Core Components
- `app.py`: Entry point. Manages overall layout, sidebar, and high-level routing between modes (Easy/Advanced).
- `ui_components.py`: Component library and high-level renderers. Acting as a bridge between `app.py` and specific tab modules.
- `ui_tabs_*.py`: Specialized renderers for each functional area.
- `state.py` (`UIStateStore`): Global state management.

---

## 2. Component Dependency Graph

### A. Entry Point: `app.py`
- **Depends on**: 
    - `streamlit_app.ui_components` (via `render_*` functions)
    - `streamlit_app.state` (`UIStateStore`, `get_session`)
    - `streamlit_app.engine_service` (`EngineService`)
    - `streamlit_app.proxy` (`UltimateHegemonyEngineProxy`)
    - `streamlit_app.background` (`TokenUsageTracker`)
- **Responsibilities**: Sidebar rendering, API Key validation, Mode switching, Health check.

### B. Bridge: `ui_components.py`
- **Depends on**:
    - `streamlit_app.ui_tabs_*` (All tab renderers)
    - `streamlit_app.proxy` (`UltimateHegemonyEngineProxy`, `run_in_background`)
    - `streamlit_app.state` (`UIStateStore`)
    - `config` (Constants)
- **Responsibilities**: `progress_fragment` (Real-time job monitoring), CSS injection, token cost display.

### C. Tab Renderers (`ui_tabs_*.py`)
- **Common Pattern**: `render_tab(state, engine, book_id)`
- **Dependencies**:
    - `streamlit_app.actions`: (CRITICAL COUPLING) Directly calls business logic functions like `actions.generate_plan`, `actions.write_episode`.
    - `streamlit_app.proxy`: Uses `UltimateHegemonyEngineProxy` for data retrieval.
    - `streamlit_app.state`: Reads/Writes runtime state via `UIStateStore`.
    - `src.core.plugin_loader`: Direct access to active plugins.

---

## 3. Coupling Analysis (The "Problem" Areas)

### 🔴 Tight Coupling: UI ➔ Actions
- **Location**: `ui_tabs_planning.py`, `ui_tabs_writing.py`, etc.
- **Issue**: UI functions directly call `actions.py` functions. 
- **Impact**: Changing a business logic parameter in `actions.py` requires editing the UI file.

### 🟠 Medium Coupling: UI ➔ Engine Proxy
- **Location**: All `render_*` functions.
- **Issue**: Passing the `engine` object deep into UI components.
- **Impact**: Hard to mock for testing; UI knows too much about the engine's internal API.

### 🟡 Low Coupling: State Management
- **Location**: `UIStateStore`
- **Issue**: Global singleton usage.
- **Impact**: State transitions are implicit, making it hard to track "what caused this UI change".

## 4. Target Decoupling Strategy
1. **Introduction of Event Bus**: Instead of `actions.generate_plan(...)`, the UI will emit a `RequestPlanEvent`.
2. **Controller Layer**: A new layer to handle events and call `actions.py`, returning results via the state store or event bus.
3. **UI Interface Protocols**: Define what a "Tab" must look like, reducing the `app.py` dependency on specific function names.
