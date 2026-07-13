# Developer Guides

This directory contains step-by-step guides for extending the Hegemony Novel Engine.

## 1. Adding a New UI Tab
`docs/guides/add_ui_tab.md`

### Overview
Adding a new functional area (e.g., "World Building" or "Character Audit" to the Streamlit interface.

### Implementation Steps
1. **Create the UI Module**:
   - Create a new file `streamlit_app/ui_tabs_[name].py`.
   - Define a `render()` function that takes the current state as an argument.
   - Use `UIStateStore` for all state interactions.
2. **Register the Page**:
   - Open `streamlit_app/pages_config.py`.
   - Add your new page to the `pages_dict` under the appropriate mode ("Easy Mode" or "Advanced Mode").
3. **Define Workflow Types (If applicable)**:
   - If the tab introduces a new type of background job, add the corresponding type to `streamlit_app/workflow_types.py`.
4. **Verify**:
   - Run `streamlit run app.py` and confirm the new tab appears in the navigation menu.

---

## 2. Creating a New Plugin
`docs/guides/add_plugin.md`

### Overview
Plugins allow you to add logic (like a new prompt modifier or data formatter) without touching the core engine.

### Implementation Steps
1. **Create Plugin Directory**:
   - Create a folder in `plugins/[plugin_name]/`.
2. **Define Plugin Logic**:
   - Create a `plugin.py` file.
   - Implement a `register()` function that the `PluginLoader` will call upon import.
   - Use the provided hook system to intercept engine calls or modify prompts.
3. **Configuration**:
   - Create a `plugin.yaml` if the plugin requires configurable parameters.
4. **Verify**:
   - Check the application logs at startup to see: `Successfully loaded plugin: plugins.[plugin_name]`.

---

## 3. State Management Best Practices
`docs/guides/state_management.md`

### The Golden Rule
**NEVER mutate `st.session_state` directly.**

### Correct Pattern
Always use `UIStateStore` to ensure type safety and persistence.

#### Reading State:
```python
# Correct
runtime = UIStateStore.get_runtime()
value = runtime.some_setting
```

#### Updating State:
```python
# Correct: Use a lambda for complex updates
UIStateStore.update(
    lambda s: setattr(s.runtime, "api_key", "new_value"), 
    notify_keys=["api_key"]
)

# Correct: Use update_runtime for simple key-value updates
UIStateStore.update_runtime("app_mode", "advanced")
```

#### Why this matters:
- **Persistence**: `UIStateStore` triggers `SessionManager` to save the state to a JSON file.
- **Reactivity**: `notify_keys` triggers registered callbacks (like `st.toast`).
- **Type Safety**: Pydantic models in `schemas/app_state.py` prevent runtime type errors.

---

## 4. Using the Resilient API Client
`docs/guides/api_client_usage.md`

### Overview
Interactions with the Backend API should use the `api_client.py` wrapper to handle network instability.

### Basic Usage
```python
from streamlit_app.api_client import APIClient

client = APIClient()
# The client automatically handles retries and timeouts based on config/resilience.yaml
response = client.post("/endpoint", json={"data": "value"})
```

### Handling Streams (SSE)
For long-running generation tasks:
```python
with client.stream("/generate", json=params) as stream:
    for chunk in stream:
        process_chunk(chunk)
```

### Error Handling
Always wrap API calls in try-except blocks using the `AppErrorHandler`:
```python
try:
    result = client.get("/data")
except Exception as e:
    AppErrorHandler.handle(e, "Failed to fetch data")
```
