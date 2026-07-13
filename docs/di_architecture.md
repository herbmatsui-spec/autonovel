# DI Architecture and Circular Reference Rules

## 1. LazyProvider Usage
To avoid circular dependencies during the initialization of the `AppContainer`, any provider that requires a method from another provider that might depend back on it must use `LazyProvider`.

**Correct Pattern:**
`generate_json = LazyProvider(AppContainer.llm, method="generate_json")`

This ensures that `AppContainer.llm()` is only called when the method is actually invoked, not when the agent is instantiated.

## 2. Initialization Order
The `AppContainer` is designed to be resolved in the following order:
1. **Infrastructure**: `api_key`, `db`, `vector_store`
2. **Core Services**: `llm_factory`, `llm`, `repo`, `pm`, `ctx_mgr`
3. **Agents**: `auditor`, `marketing`, `bible_generator`, `plot_expander`, `planner`, `narrative`, `critique`, `writer`

## 3. Circularity Prohibition
Direct circular dependencies between `SingletonProvider` definitions are strictly prohibited. If a circular dependency is detected (e.g., Agent A $\rightarrow$ Agent B $\rightarrow$ Agent A), the dependency must be broken using:
- `LazyProvider` for method-level dependencies.
- Moving shared logic to a separate `Service` or `Kernel`.
