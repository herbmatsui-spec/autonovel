from src.core.observability import TraceContext


def test_trace_context_set_get():
    TraceContext.set_trace_id("test-123")
    assert TraceContext.get_trace_id() == "test-123"
    TraceContext.clear()
    # clear 後は新規 ID が生成される
    new_id = TraceContext.get_trace_id()
    assert new_id != "test-123"
    TraceContext.clear()


def test_trace_context_isolated():
    TraceContext.set_trace_id("a")
    assert TraceContext.get_trace_id() == "a"
    TraceContext.clear()
    TraceContext.set_trace_id("b")
    assert TraceContext.get_trace_id() == "b"
    TraceContext.clear()
