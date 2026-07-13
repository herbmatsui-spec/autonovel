# Streamlit Fragment & State Map

## 1. Fragment Map
Current `@st.fragment` usage across the application.

| File | Function | Line | Config | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| `streamlit_app/sidebar.py` | `render_forbidden_patterns` | 143 | Default | Forbidden patterns configuration |
| `streamlit_app/sidebar.py` | `render_emotional_hook` | 162 | Default | Emotional hook settings |
| `streamlit_app/sidebar.py` | `render_reader_desires` | 183 | Default | Reader desires settings |
| `streamlit_app/ui_components.py` | `progress_dispatcher` | 139 | `run_every=PROGRESS_POLL_INTERVAL_SEC` | Periodic progress polling |
| `streamlit_app/ui_components.py` | `status_display_fragment` | 153 | Default | Current job status display |
| `streamlit_app/ui_components.py` | `next_steps_fragment` | 187 | Default | Job result next steps |
| `streamlit_app/ui_components.py` | `log_fragment` | 217 | Default | Log streaming/display |
| `streamlit_app/ui_components.py` | `token_usage_fragment` | 234 | Default | Token usage display |
| `streamlit_app/ui_tabs_writing.py` | `render_plot_tab` | 12 | Default | Plotting tab content |
| `streamlit_app/ui_tabs_writing.py` | `render_episode_list` | 100 | Default | Episode list management |
| `streamlit_app/ui_tabs_writing.py` | `render_import_tab` | 138 | Default | Chapter import interface |
| `streamlit_app/ui_tabs_writing.py` | `render_writing_tab` | 154 | Default | Writing interface |
| `streamlit_app/ui/components/widgets.py` | `progress_fragment` | 56 | Default | Generic progress widget |

## 2. Session State Map
Identified `st.session_state` keys and their roles.

| Key | File | Usage | Note |
| :--- | :--- | :--- | :--- |
| `_STATE_KEY` (via `AppStateModel`) | `streamlit_app/state.py` | Global state persistence | Core application state |
| `css_injected` | `streamlit_app/ui_components.py` | Boolean flag | Prevents duplicate CSS injection |
| `easy_mode_loaded` | `streamlit_app/ui_tabs_planning.py` | Boolean flag | Tab initialization guard |
| `planning_tab_loaded` | `streamlit_app/ui_tabs_planning.py` | Boolean flag | Tab initialization guard |
| `nsfw_consented` | `streamlit_app/ui/components/nsfw_disclaimer.py` | Boolean flag | User consent for NSFW content |
| `[idx_key]` (dynamic) | `streamlit_app/ui_components.py` | Integer | Log scroll position / index |

## 3. Redraw Analysis
- **Polling**: `progress_dispatcher` is the only fragment with `run_every`, causing periodic updates.
- **Static Fragments**: Many fragments in `ui_tabs_writing.py` and `sidebar.py` are defined but may still trigger full app reruns if they modify `st.session_state` without careful management.
- **Initialization**: Use of `st.rerun()` after setting `_loaded` flags in `ui_tabs_planning.py` causes full page re-execution.
