# TODO: Reduce overly broad exception handling

The following files have a high number of `except Exception` clauses that should be narrowed to specific exceptions and include `trace_id` in logs for better traceability:

1. `src/backend/tasks.py`
2. `src/backend/workflows/writing_langgraph.py`
3. `src/backend/database/core.py`

For each, review the `except Exception` blocks and replace with more specific exception types where possible. Add `trace_id` to log statements (e.g., `logger.error(..., trace_id=TraceContext.get_trace_id())`).

This improves debuggability and prevents masking of unexpected errors.