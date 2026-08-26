# DI Dependency Map (Delayed References)

This document tracks delayed references (lambdas) in `AppContainer` and their target dependencies to visualize the dependency graph and identify circular reference risks.

## Delayed References via Lambdas

| Provider | Argument | Target Provider | Target Method | Type |
| :--- | :--- | :--- | :--- | :--- |
| `auditor` | `generate_json` | `llm` | `generate_json` | Method-level Delay |
| `marketing` | `generate_json` | `llm` | `generate_json` | Method-level Delay |
| `planner` | `generate_json` | `llm` | `generate_json` | Method-level Delay |
| `validator` | `generate_json` | `llm` | `generate_json` | Method-level Delay |
| `narrative` | `generate_json` | `llm` | `generate_json` | Method-level Delay |
| `critique` | `generate_json` | `llm` | `generate_json` | Method-level Delay |
| `audit_service_factory` | `_provide_audit_service` | `repo`, `llm`, `pm` | N/A | Factory-level Delay |

## Dependency Graph (Core)

- `AppContainer.llm` $\rightarrow$ `llm_factory` $\rightarrow$ `genai_client`, `cooldown`
- `AppContainer.repo` $\rightarrow$ `db`
- `AppContainer.pm` $\rightarrow$ (No internal provider dependencies)
- `AppContainer.ctx_mgr` $\rightarrow$ `repo`

## Agent Dependencies (Potential Circularity)

- `auditor` $\rightarrow$ `repo`, `pm`, `llm` (via lambda), `ctx_mgr`
- `marketing` $\rightarrow$ `repo`, `pm`, `llm` (via lambda)
- `planner` $\rightarrow$ `repo`, `pm`, `llm` (via lambda), `ctx_mgr`, `auditor`, `bible_generator`, `plot_expander`, `audit_service_factory`
- `bible_generator` $\rightarrow$ `repo`, `llm`, `pm`, `marketing`, `auditor`
- `plot_expander` $\rightarrow$ `repo`, `llm`, `pm`, `auditor`
- `narrative` $\rightarrow$ `llm` (via lambda), `repo`, `pm`, `ctx_mgr`, `validator`, `auditor`
- `critique` $\rightarrow$ `repo`, `pm`, `llm` (via lambda)
- `writer` $\rightarrow$ `repo`, `llm`, `pm`, `narrative`, `ctx_mgr`, `critique`, `plot_expander`, `style_rag`, `uow`, `global_config`, `planner`

## Analysis
The most critical potential for circularity is around the `Planner` $\leftrightarrow$ `PlotExpander`/`BibleGenerator` $\leftrightarrow$ `Auditor` loop. However, currently, `llm` is the primary target of lambdas, and `llm` itself has no dependencies on the agents, breaking the potential cycle at the LLM level.
