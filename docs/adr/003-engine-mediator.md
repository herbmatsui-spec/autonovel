# ADR-003: Engine Mediator Architecture

**Date:** 2026-07-07
**Status:** Accepted
**Decider(s):** Zoo (Software Engineer)

### 1. Context and Problem Statement
The application requires a way to interact with a complex LLM-driven narrative engine. The engine involves multiple components: prompt registries, LLM gateways, and stateful session management. Directly calling these from the Streamlit UI would lead to:
- UI code cluttered with business logic and prompt construction.
- Difficulty in swapping the LLM provider or engine implementation without rewriting UI components.
- Inconsistent handling of asynchronous operations (async/await) within the synchronous Streamlit execution model.
- Lack of a centralized point for caching, logging, and validation of engine responses.

### 2. Decision to be Made
Define a mediation layer that decouples the User Interface from the Core Engine logic.

### 3. Considered Options
- **Option 1: Direct Service Injection**
  - Pros: Simple, direct access to all engine capabilities.
  - Cons: UI components become tightly coupled to the `LLMService` and `EngineService` internal APIs.
- **Option 2: Proxy Pattern via a Dedicated Mediator (`EngineService` + `UltimateHegemonyEngineProxy`)**
  - Pros: Provides a simplified, UI-centric interface. Hides the complexity of async boundaries. Allows for "dry-run" or "mock" modes for UI testing.
  - Cons: Adds an extra layer of indirection.
- **Option 3: API-First Backend (REST/gRPC)**
  - Pros: Complete separation of concerns; allows the engine to run on a separate server.
  - Cons: Significant overhead for the current development phase; requires managing network latency and API versioning.

### 4. Decision Outcome
**Chosen Option: Option 2 (Proxy Pattern via a Dedicated Mediator)**

**Justification:**
The mediator pattern (implemented via `EngineService` and the proxy layer in `streamlit_app/engine.py`) allows the UI to request high-level actions (e.g., "generate plot") without needing to know how prompts are assembled or how the LLM gateway is configured. This ensures that changes to the narrative engineering logic (prompts, templates) do not require changes to the UI layout.

### 5. Consequences
- **Positive:**
  - **Decoupling:** The UI only knows "what" to do, while the mediator knows "how" to do it.
  - **Consistency:** Centralized error handling and logging for all engine interactions.
  - **Testability:** The mediator can be easily mocked for frontend-only development.
- **Negative/Trade-offs:**
  - **Indirection:** Adding a new engine feature requires updating both the core service and the mediator/proxy layer.
- **Risks:**
  - If the mediator becomes too large ("God Object"), it may become a bottleneck for development.

### 6. Alternatives’ Trade-offs
Option 1 was rejected due to the high risk of UI/Logic entanglement. Option 3 was deemed premature for the current scale, though the mediator pattern provides a clean path toward a full API-first architecture in the future.

### 7. Notes/References
- Implementation: [`src/engine_service.py`](src/engine_service.py), [`streamlit_app/engine.py`](streamlit_app/engine.py)
- Core LLM Logic: [`src/services/llm_service.py`](src/services/llm_service.py)
