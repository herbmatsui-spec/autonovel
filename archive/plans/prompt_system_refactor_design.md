# Prompt System Refactor Design Spec

## 1. PromptManager Role Decomposition (Builder Pattern)

The current `PromptManager` is a "God Class" that handles both the coordination of rendering and the specific business logic for every single prompt in the system.

### New Architecture
We will split `PromptManager` into three layers:
1. **`PromptRegistry`**: (Existing/Enhanced) Low-level template resolution (FS, DB, Cache).
2. **`PromptBuilder` (New Strategy Layer)**: Specialized classes that know *what* data a specific prompt needs and *how* to format it.
3. **`PromptManager` (New Coordinator)**: A thin wrapper that delegates to the correct Builder.

### Class Structure
- `BasePromptBuilder`: Abstract base class.
    - `render(context: PromptContext, book_id: Optional[int]) -> str`
- `AuditPromptBuilder`: Handles all `build_*_audit_prompt` methods.
- `NarrativePromptBuilder`: Handles `build_world_creation`, `build_mc_creation`, `build_plot_expansion`.
- `WritingPromptBuilder`: Handles `build_drafting_prompt`, `build_final_writing_prompt`, `build_polishing_prompt`.
- `UtilityPromptBuilder`: Handles marketing, title generation, etc.

### Data Flow
`User/Service` $\to$ `PromptManager` $\to$ `SpecificBuilder` $\to$ `PromptRegistry` $\to$ `Jinja2` $\to$ `String`

---

## 2. Domain-Specific Exceptions & Error Handling

To prevent `Any` or generic `Exception` catches, we define a hierarchy.

### Exception Hierarchy
- `PromptError` (Base)
    - `PromptTemplateNotFoundError`: Raised when a `.j2` file is missing.
    - `PromptRenderingError`: Raised when Jinja2 fails to render due to missing keys.
    - `PromptContextError`: Raised when required Pydantic fields are missing/invalid.
    - `PromptRegistryError`: Base for registry-specific failures.
        - `PromptCacheError`: Cache corruption or failure.
        - `PromptDbError`: Failure to fetch override from DB.

### Standard Handling Pattern
```python
try:
    prompt = await prompt_manager.build_writing_prompt(...)
except PromptContextError as e:
    logger.error(f"Invalid context provided: {e}")
    # Fallback or raise to API layer
except PromptError as e:
    logger.critical(f"Systemic prompt failure: {e}")
    raise
```

---

## 3. Type Strictness (Pydantic/TypedDict)

Eliminate `Any` and `Dict[str, Any]` for prompt contexts.

### Core Context Models
- `PromptContext` (Base Pydantic Model)
- `AuditContext(PromptContext)`: fields for `synopsis`, `world_settings`, `schema_json`.
- `WritingContext(PromptContext)`: fields for `char_static_ctx`, `char_dynamic_ctx`, `blueprint`, `script_text`.
- `PlotExpansionContext(PromptContext)`: fields for `past_plots`, `arcs`, `ep_info`.

### Registry Interface Update
`PromptRegistry.render_async(template_name: str, context: BaseModel, book_id: Optional[int])`
Inside `render_async`, we use `context.model_dump()` to pass data to Jinja2.

---

## 4. PromptRegistry Metrics External Integration

The current `_metrics` dict is volatile (in-memory). We need a bridge to external monitoring (e.g., Prometheus, CloudWatch, or a simple DB table).

### Design: `MetricsCollector` Interface
1. **`IMetricsCollector` (Abstract)**:
    - `record_hit(template_name, duration_ms, error)`
    - `flush()`
2. **`InMemoryCollector`**: (Current implementation)
3. **`PrometheusCollector`**: (New) Uses `prometheus_client` to export counters/histograms.
4. **`DatabaseCollector`**: (New) Periodically writes aggregate stats to `prompt_metrics` table.

### Integration Point
`PromptRegistry` will now take an `IMetricsCollector` in its constructor:
`self.metrics_collector = metrics_collector or InMemoryCollector()`
The `record_hit` method will delegate directly to this collector.

---

## 5. Low-Performance LLM Implementation Guidelines

To ensure a low-tier LLM can implement this without "hallucinating" or skipping steps:

1. **No Logic-in-Diffs**: Do not ask the LLM to "refactor the logic." Instead, provide the exact target code for a specific function.
2. **Atomic Commits**: One file change per step.
3. **Verification Steps**: Every change must be followed by a "Verification" step (e.g., "Run `pytest tests/prompts/test_registry_perf.py` and verify no regressions").
4. **Explicit Imports**: Always specify exactly which line to add the import on.
5. **No Placeholders**: Ban `// ... rest of code remains the same`. The LLM must use `apply_diff` with exact search blocks.
