# ADR-001: State Management Architecture

**Date:** 2026-07-07
**Status:** Accepted
**Decider(s):** Zoo (Software Engineer)

### 1. Context and Problem Statement
Streamlit applications inherently suffer from a "rerun-everything" model where the script executes from top to bottom on every user interaction. This makes maintaining complex, type-safe, and persistent state across different pages and components challenging. Direct use of `st.session_state` often leads to:
- Lack of type safety (everything is `Any`).
- Circular dependency issues when state is needed across multiple modules.
- Difficulty in implementing "undo/redo" or session persistence to disk.
- Spaghetti code where UI components directly mutate global state.

### 2. Decision to be Made
Define a robust mechanism to manage application state that ensures type safety, centralizes access, and supports persistence.

### 3. Considered Options
- **Option 1: Direct `st.session_state` Usage**
  - Pros: Simple, no boilerplate, native to Streamlit.
  - Cons: No type safety, prone to `KeyError`, state mutation is scattered across the codebase.
- **Option 2: Global Singleton Object**
  - Pros: Type safety via Python classes.
  - Cons: Does not survive Streamlit reruns (unless wrapped in session state), threading issues.
- **Option 3: Centralized Store with Pydantic Models (`UIStateStore` + `AppStateModel`)**
  - Pros: Strong typing, centralized mutation logic, easy serialization to JSON for persistence, decoupled from UI.
  - Cons: Requires more boilerplate code (Store and Model classes).

### 4. Decision Outcome
**Chosen Option: Option 3 (Centralized Store with Pydantic Models)**

**Justification:**
The complexity of the "Hegemony Novel Engine" requires a high degree of state consistency (e.g., keeping track of active background jobs, wizard steps, and runtime configurations). Pydantic provides the necessary validation and serialization. The `UIStateStore` acts as a Mediator/Facade, ensuring that UI components do not touch `st.session_state` directly, thus reducing the risk of side-effect bugs during reruns.

### 5. Consequences
- **Positive:**
  - **Type Safety:** IDEs can provide autocomplete for state attributes.
  - **Persistence:** State is automatically saved to `storage/session_{id}.json`, allowing users to recover work.
  - **Maintainability:** State mutation logic is encapsulated in `UIStateStore.update()`, making it easier to debug and add observers (subscriptions).
- **Negative/Trade-offs:**
  - **Indirection:** Accessing a simple value requires calling `UIStateStore.get_runtime().value` instead of `st.session_state.value`.
  - **Boilerplate:** Any new state variable must be added to the Pydantic model first.
- **Risks:**
  - Over-reliance on the `SessionManager` for disk I/O might introduce latency if the state object becomes massive.

### 6. Alternatives’ Trade-offs
Option 1 was rejected because it is unsuitable for a professional-grade tool with complex data flows. Option 2 was rejected because it violates the Streamlit execution model.

### 7. Notes/References
- Implementation: [`streamlit_app/state.py`](streamlit_app/state.py)
- Model Definition: [`schemas/app_state.py`](schemas/app_state.py)
