# API Call & State Mapping

## 1. API Endpoint Mapping
Current API methods in `streamlit_app/api_client.py` and their expected usage.

| Method | Endpoint | Type | State Dependency | Frequency | Optimization Candidate |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `start_plan_generation` | `/plan/generate` | POST | `AppStateModel` | Low | No (Triggered by user) |
| `start_plot_expansion` | `/plot/expand` | POST | `AppStateModel` | Low | No (Triggered by user) |
| `start_episode_writing` | `/writing/start` | POST | `AppStateModel` | Low | No (Triggered by user) |
| `get_task_status` | `/tasks/{task_id}` | GET | `run_key` (from state) | High | **Yes (Polling)** |
| `stop_task` | `/tasks/{task_id}/stop` | POST | `run_key` | Low | No |
| `start_erotic_refinement` | `/refine_erotic` | POST | `AppStateModel`, User Input | Low | No (Triggered by user) |

## 2. Session State $\rightarrow$ API Call Chain
How `st.session_state` triggers API calls.

- **Polling Loop**: `st.session_state["run_key"]` $\rightarrow$ `get_task_status(task_id)` $\rightarrow$ Triggered by `@st.fragment(run_every=...)` in `progress_dispatcher`.
- **Initialization**: `st.session_state["planning_tab_loaded"]` $\rightarrow$ If False, may trigger initial data fetch via API.
- **Action Trigger**: User Input $\rightarrow$ `st.session_state` Update $\rightarrow$ `start_*` API Call $\rightarrow$ `st.session_state["run_key"]` updated.

## 3. Redundancy Analysis
- **Over-polling**: If multiple fragments call `get_task_status` for the same `task_id` during the same rerun, it creates redundant network traffic.
- **State-based Reruns**: Setting flags like `easy_mode_loaded = True` followed by `st.rerun()` causes the entire app to execute, potentially re-calling "get" APIs that could be cached.
- **Lack of Memoization**: Basic GET requests (if any are added for metadata) are currently not cached, relying entirely on `AppStateModel` persistence.
