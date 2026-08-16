# Detailed Implementation Plan: Prompt System Refactor

This document_version: 1.0
target_audience: Implementation LLM (Low-performance optimized)
objective: Refactor `PromptManager` and `PromptRegistry` for better maintainability, type safety, and observability.

---

## 0. Implementation Guidelines for LLM
**CRITICAL: Failure to follow these guidelines will result in broken code.**

1. **No Placeholders**: Never use `// ... rest of code remains the same` or `# ... (existing code)`. You must provide the full content or exact search/replace blocks.
2. **Atomic Changes**: Perform one logical change per step. Do not combine "adding a class" and "updating a caller" in one step unless they are in the same file and tightly coupled.
3. **Strict Imports**: Always add imports at the top of the file. Specify the exact line if possible.
4. **Verification First**: After every 3-5 steps, you must verify the changes by running existing tests or adding a minimal test case.
5. **No Logic Assumptions**: If the spec says "Update method X to use Y", do not "improve" method X's logic unless explicitly told to.

---

## 1. Implementation Roadmap (Atomic Steps)

### Phase 1: Infrastructure & Type Definitions
*Goal: Create the foundation without breaking existing functionality.*

- [ ] **Step 1.1**: Create `autonovel/prompts/exceptions.py`. Define `PromptError`, `PromptTemplateNotFoundError`, `PromptRenderingError`, `PromptContextError`, `PromptRegistryError`, `PromptCacheError`, and `PromptDbError`.
- [ ] **Step 1.2**: Create `autonovel/prompts/schemas.py`. Define `PromptContext` (BaseModel), `AuditContext`, `WritingContext`, `PlotExpansionContext`, and `UtilityContext` using Pydantic.
- [ ] **Step 1.3**: Create `autonovel/prompts/metrics.py`. Define `IMetricsCollector` (ABC), `InMemoryCollector`, and `PrometheusCollector` (if `prometheus_client` is available).

### Phase 2: PromptRegistry Enhancement
*Goal: Upgrade the registry to support new types and metrics.*

- [ ] **Step 2.1**: Update `autonovel/prompts/registry.py`: Import `PromptError` hierarchy from `prompts.exceptions`.
- [ ] **Step 2.2**: Update `autonovel/prompts/registry.py`: Replace `_metrics` dict with `IMetricsCollector` injection in `__init__`.
- [ ] **Step 2.3**: Update `autonovel/prompts/registry.py`: Update `record_hit` to delegate to `self.metrics_collector`.
- [ ] **Step 2.4**: Update `autonovel/prompts/registry.py`: Modify `render_async` and `render` to accept `PromptContext` (Pydantic) instead of `Dict[str, Any]`. Use `context.model_dump()` internally.
- [ ] **Step 2.5**: Update `autonovel/prompts/registry.py`: Replace generic `Exception` catches in `_get_template_source_sync` with `PromptTemplateNotFoundError` and `PromptRegistryError`.

### Phase 3: PromptBuilder Layer Implementation
*Goal: Extract business logic from PromptManager into specialized builders.*

- [ ] **Step 3.1**: Create `autonovel/prompts/builders/base.py`. Define `BasePromptBuilder` abstract class.
- [ ] **Step 3.2**: Create `autonovel/prompts/builders/audit.py`. Implement `AuditPromptBuilder` migrating methods: `build_producer_audit_prompt`, `build_plot_integrity_audit_prompt`, `build_logical_audit_prompt`, `build_foreshadowing_audit_prompt`, `build_tension_audit_prompt`.
- [ ] **Step 3.3**: Create `autonovel/prompts/builders/narrative.py`. Implement `NarrativePromptBuilder` migrating methods: `build_world_creation_prompt`, `build_mc_creation_prompt`, `build_plot_expansion_prompt`, `build_bible_creation_prompt`, `build_roadmap_prompt`.
- [ ] **Step 3.4**: Create `autonovel/prompts/builders/writing.py`. Implement `WritingPromptBuilder` migrating methods: `build_drafting_prompt`, `build_final_writing_prompt`, `build_polishing_prompt`, `build_fw_prompt`.
- [ ] **Step 3.5**: Create `autonovel/prompts/builders/utility.py`. Implement `UtilityPromptBuilder` migrating remaining methods (marketing, title, etc.).

### Phase 4: PromptManager Refactoring
*Goal: Turn PromptManager into a clean coordinator.*

- [ ] **Step 4.1**: Update `autonovel/prompts/manager.py`: Import all new Builders and `PromptContext` schemas.
- [ ] **Step 4.2**: Update `autonovel/prompts/manager.py`: Initialize builders in `__init__` (e.g., `self.audit_builder = AuditPromptBuilder(self.registry)`).
- [ ] **Step 4.3**: Update `autonovel/prompts/manager.py`: Refactor `build_producer_audit_prompt` to call `self.audit_builder.build(...)`.
- [ ] **Step 4.4**: (Repeat for all other `build_*` methods across all builders).
- [ ] **Step 4.5**: Remove all private helper methods from `PromptManager` (like `_build_quota_section`) and move them into the respective `PromptBuilder` classes.

### Phase 5: Cleanup & Verification
*Goal: Ensure no `Any` remains and system is stable.*

- [ ] **Step 5.1**: Run `ruff check .` and fix any remaining type hints.
- [ ] **Step 5.2**: Execute `pytest tests/prompts/test_registry_perf.py` and `tests/integration/test_prompt_compare.py`.
- [ ] **Step 5.3**: Verify that DB overrides still work through the new Builder $\to$ Registry path.

---

## 2. Technical Specification Details

### Exception Mapping
| Current Error | New Exception | Context |
|---|---|---|
| `FileNotFoundError` | `PromptTemplateNotFoundError` | Template file missing |
| `jinja2.exceptions.TemplateError` | `PromptRenderingError` | Variable missing in template |
| `TypeError` / `KeyError` | `PromptContextError` | Pydantic validation failure |
| `db_manager` errors | `PromptDbError` | DB connection/query failure |

### Type strictness Example (WritingContext)
```python
class WritingContext(BaseModel):
    title: str
    ep_num: int
    static_ctx: str
    dyn_ctx: str
    prev_ctx: str
    blueprint: str
    extra_instruction: str = ""
    # ... other necessary fields
```

### Metrics Bridge Design
The `PromptRegistry` will no longer manage the state of metrics.
```python
class PromptRegistry:
    def __init__(self, ..., metrics_collector: IMetricsCollector):
        self.metrics_collector = metrics_collector

    def record_hit(self, template_name, duration, error):
        self.metrics_collector.record_hit(template_name, duration, error)
```
