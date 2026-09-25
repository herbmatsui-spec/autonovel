# ADR 001: Writing Service Consolidation

## Context

The codebase currently has three separate writing service implementations that have diverged over time:

1. **`src/backend/writing_service.py`** - Handles writing pipeline execution and EngineFacade integration
2. **`src/services/writing_service.py`** - Handles BookScore evaluation and auto-regeneration loops
3. **`src/services/writing_services.py`** (referenced but doesn't exist as file) - Would handle state validation and ProjectContext integration

This fragmentation causes:
- Duplicate code and inconsistent interfaces
- Difficult maintenance and testing
- Unclear ownership of responsibilities
- Import confusion for consumers

## Decision

Consolidate all writing-related functionality into a single `src/domain/writing/` package with the following structure:

```
src/domain/writing/
├── __init__.py          # WritingService facade (public API)
├── coordinator.py       # WritingCoordinator - pipeline execution core
├── quality_loop.py      # QualityLoop - BookScore evaluation & regeneration
├── state_guard.py       # StateGuard - pre-validation & context checks
└── models.py            # Shared data models (WritingGenerationContext, etc.)
```

### Component Responsibilities

| Component | Responsibility | Source |
|-----------|----------------|--------|
| `WritingCoordinator` | Pipeline execution, episode generation, writer delegation | `src/backend/writing_service.py` |
| `QualityLoop` | BookScore calculation, threshold checking, regeneration orchestration | `src/services/writing_service.py` |
| `StateGuard` | ProjectContext validation, chapter sequence validation | `src/services/writing_services.py` (conceptual) |
| `WritingService` (facade) | Unified public API, backward compatibility | New |

### Backward Compatibility Strategy

The three legacy files will become thin compatibility shims that delegate to the new unified `WritingService`:

```python
# src/backend/writing_service.py
from src.domain.writing import WritingService
WritingService = WritingService  # alias

# src/services/writing_service.py
from src.domain.writing import WritingService
class WritingService(WritingService):  # inherit for any custom extensions
    pass

# src/services/writing_services.py (new file if needed)
from src.domain.writing import WritingService
WritingServices = WritingService  # alias
```

## Interface Mapping

### WritingCoordinator (from `src/backend/writing_service.py`)

| Method | Signature |
|--------|-----------|
| `generate_episodes_pipeline` | `(book_id, start_ep, end_ep, passion, target_word_count, is_easy_mode, reporter, branch_id, style_tag) -> tuple[int, list]` |
| `generate_episodes` | `(book_id, start_ep, end_ep, passion, target_word_count, is_easy_mode, reporter, branch_id, style_tag, auto_regenerate, max_retries) -> int` |
| `audit_generated_text` | `(text) -> dict` |
| `calculate_book_score` | `(book_id, chapter_number, genre, phase) -> dict \| None` |
| `analyze_and_import_chapter` | `(book_id, ep_num, import_text, do_refine) -> Any` |
| `_trigger_pdca_rewrite` | Internal helper |

### QualityLoop (from `src/services/writing_service.py`)

| Method | Signature |
|--------|-----------|
| `generate_with_quality_assurance` | `(ctx, reporter) -> AgentResult` |
| `_identify_low_dimensions` | `(book_score) -> list[str]` |
| `_determine_regeneration_action` | `(low_dimensions) -> RegenerationAction` |

### StateGuard (new, based on conceptual `src/services/writing_services.py`)

| Method | Signature |
|--------|-----------|
| `validate_project_context` | `(project_ctx) -> ValidationResult` |
| `ensure_chapter_sequence` | `(book_id, start_ep, end_ep) -> bool` |

### WritingService Facade (unified public API)

Exposes all public methods from the three components, maintaining backward compatibility.

## Implementation Steps

1. Extract all public method signatures from the three source files
2. Create `WritingCoordinator` in `src/domain/writing/coordinator.py`
3. Create `QualityLoop` in `src/domain/writing/quality_loop.py`
4. Create `StateGuard` in `src/domain/writing/state_guard.py`
5. Create shared models in `src/domain/writing/models.py`
6. Create `WritingService` facade in `src/domain/writing/__init__.py`
7. Update three legacy files as compatibility shims
8. Update DI container bindings
9. Run all writing-related tests

## Consequences

### Positive
- Single source of truth for writing logic
- Clear separation of concerns (coordination, quality, validation)
- Easier testing with focused unit tests per component
- Cleaner imports for consumers

### Negative
- Initial migration effort
- Temporary compatibility shim maintenance
- Need to update all imports across codebase (mitigated by shims)

## Testing

- Unit tests for each component: `test_coordinator.py`, `test_quality_loop.py`, `test_state_guard.py`
- Facade integration test: `test_writing_service_facade.py`
- Existing tests must pass: `test_editor_autosave.py`, `test_writing_graph_flow.py`
- Full regression: `pytest tests/unit/services/test_editor_autosave.py tests/unit/workflows/test_writing_graph_flow.py`