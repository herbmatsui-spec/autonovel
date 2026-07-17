# ADR-0004: Engine Decomposition (Facade + Domain Services)

**Date:** 2026-07-17
**Status:** Accepted
**Decider(s):** Kilo (Software Engineer)

### 1. Context and Problem Statement
`UltimateHegemonyEngine` (`src/backend/engine.py`) is the central integration point for all narrative-generation logic. Its constructor accepts 18 positional dependencies (effectively 42 if counting aliases and injected sub-objects), and it holds responsibilities spanning planning, writing, critique, bible management, tension-curve computation, and formatting. This creates:

- A "God Object" that is hard to test in isolation (every unit test must supply all 18 collaborators).
- High change-impact: any new capability (e.g. a new writer mode) requires editing the monolith constructor and the `AppContainer` wiring.
- Duplicated delegation logic across 11 workflow classes (`engine.writer...`, `engine.planner...`, etc.).
- Ambiguous aliases (`self.planner = bible_agent`, `self.ai_api = llm`) that confuse readers.

### 2. Decision to be Made
Restructure the engine boundary into a thin Facade plus focused domain services, without breaking existing callers during the transition.

### 3. Considered Options
- **Option 1: Keep the monolith, add helper methods**
  - Pros: Zero migration risk.
  - Cons: Does not address root cause; complexity keeps growing.
- **Option 2: Facade + 5 Domain Services (Strangler Fig)**
  - Pros: Single-responsibility services, testable in isolation, workflows depend on narrow Protocols, backward-compatible Facade lets migration proceed incrementally.
  - Cons: Temporary dual structure (Facade + legacy engine) during migration; more files.
- **Option 3: Full rewrite behind a new API**
  - Pros: Cleanest end state.
  - Cons: High risk, long-lived branch, no incremental value delivery.

### 4. Decision Outcome
**Chosen Option: Option 2 (Facade + 5 Domain Services via Strangler Fig)**

**Justification:**
The Facade preserves the existing `engine.*` call surface so every workflow, router, and Streamlit page keeps working untouched. Behind it, responsibilities are extracted into five services:

| Service | Responsibility | Protocol |
| --- | --- | --- |
| `PlanningService` | 企画・プロット生成 | `PlanningPort` |
| `WritingService` | 本文執筆・研磨 | `WritingPort` |
| `CritiqueService` | 品質分析・監査 | `CritiquePort` |
| `BibleService` | 設定集ライフサイクル | `BiblePort` |
| `TensionService` | テンション曲線・カタルシス | `TensionPort` |

A minimal `CoreEngine` owns only transaction/repository boundaries. Shared interfaces are expressed via `typing.Protocol` so any service can be swapped or mocked without import cycles.

### 5. Consequences
- **Positive:**
  - Each service is unit-testable with only its real collaborators.
  - Workflows depend on narrow `Protocol`s, reducing coupling and import cycles.
  - New capabilities land in one service, not the monolith.
- **Negative/Trade-offs:**
  - Temporary dual structure (Facade + legacy `UltimateHegemonyEngine`) during migration.
  - More modules to navigate.
- **Risks:**
  - Forgetting to migrate a caller; mitigated by grep gates ("Engineering Gate") at each phase boundary and a final `grep -r "UltimateHegemonyEngine"`.

### 6. Alternatives’ Trade-offs
Option 1 was rejected as it only delays the problem. Option 3 was rejected as premature and high-risk for the current scale; Option 2 provides a clean path while delivering value incrementally (the Facade already removes the 42-arg burden from callers).

### 7. Notes/References
- Implementation plan: [`docs/engine_refactoring_200_steps.md`](engine_refactoring_200_steps.md)
- Protocols: `src/backend/protocols.py`
- Facade: `src/backend/engine_facade.py`
- Services: `src/backend/{planning,writing,critique,bible,tension}_service.py`
- Container wiring: `src/core/container.py` (`AppContainer`), `config/container.py` (`Container`)
- Related: [ADR-003 Engine Mediator](003-engine-mediator.md)
