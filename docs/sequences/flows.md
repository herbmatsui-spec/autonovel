# System Sequences

This directory contains Mermaid sequence diagrams illustrating the key data flows of the Hegemony Novel Engine.

## 1. Application Startup Sequence
`docs/sequences/startup.mmd`

```mermaid
sequenceDiagram
    participant User
    participant App as app.py (Orchestrator)
    participant PL as PluginLoader (Plugin Hub)
    participant HC as health_check.py (Reliability Agent)
    participant SS as state.py (State Keeper)
    participant SB as sidebar.py
    participant Nav as pages_config.py (Navigation)

    User->>App: Start Application
    App->>SS: _init_session()
    App->>PL: load_all_plugins()
    PL->>PL: Scan /plugins/*.py
    PL->>PL: Dynamic Import & Register
    App->>HC: ensure_backend_available()
    HC->>Backend: GET /health
    Backend-->>HC: 200 OK
    App->>SB: render_sidebar()
    SB-->>User: Show API Key Input
    User->>SB: Input API Key
    SB-->>App: return api_key
    App->>Nav: get_pages(mode)
    Nav-->>App: Return Page List
    App->>User: Render Navigation Menu
```

## 2. Generation Request Sequence
`docs/sequences/generation.mmd`

```mermaid
sequenceDiagram
    participant UI as UI Tab (Writing/Planning)
    participant Proxy as Engine Proxy
    participant Svc as EngineService (Mediator)
    participant API as Backend API (FastAPI)
    participant Engine as Core Engine Logic
    participant LLM as LLM Gateway / Gemini

    UI->>Proxy: trigger_generation(params)
    Proxy->>Svc: generate_plot(prompt)
    Svc->>API: POST /generate (async request)
    API->>Engine: Process Narrative Logic
    Engine->>LLM: Request completion
    LLM-->>Engine: Streamed Response
    Engine-->>API: Processed JSON/Text
    API-->>Proxy: SSE Stream / JSON Response
    Proxy-->>UI: Update State / Display Result
    UI->>UI: Re-render with new content
```

## 3. State Change & Notification Flow
`docs/sequences/state_change.mmd`

```mermaid
sequenceDiagram
    participant UI as UI Component
    participant Store as UIStateStore
    participant SM as SessionManager
    participant Disk as storage/*.json
    participant Callback as Registered Subscriber

    UI->>Store: update(update_func, notify_keys)
    Store->>Store: increment_rerun_count()
    Store->>SM: get_state()
    SM->>Store: AppStateModel
    Store->>Store: Apply update_func(state)
    Store->>SM: save_state(state)
    SM->>Disk: Write JSON
    Store->>Store: _notify(key, value)
    Store->>Callback: execute callback(value)
    Callback->>UI: Trigger st.toast / UI Change
```

## 4. Plugin Loading Flow
`docs/sequences/plugin_load.mmd`

```mermaid
sequenceDiagram
    participant App as app.py
    participant PL as PluginLoader
    participant FS as Filesystem (/plugins)
    participant Mod as Plugin Module

    App->>PL: load_all_plugins()
    PL->>FS: glob("*.py")
    FS-->>PL: List of .py files
    loop For each plugin file
        PL->>PL: Filter __init__.py / _*.py
        PL->>Mod: importlib.import_module(module_name)
        Mod->>Mod: Execute top-level registration
        Mod-->>PL: Module loaded
    end
    PL-->>App: All plugins initialized
```
