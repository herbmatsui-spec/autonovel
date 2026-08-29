"""tests/unit/test_consistency_engine.py"""
from src.consistency.findings import Finding, Evidence
from src.consistency.engine import ConsistencyEngine
from src.consistency.checkers.base import Checker, CheckContext
from src.consistency.filters import filter_intentional
from typing import List


class _DummyChecker(Checker):
    name = "dummy"
    category = "timeline"

    def check(self, context: CheckContext) -> List[Finding]:
        return [self._make_finding("high", "test finding")]


def test_finding_key_stable():
    f = Finding(category="x", description="abc" * 20)
    assert f.key().startswith("x:abc")


def test_engine_runs_checkers():
    engine = ConsistencyEngine([_DummyChecker()])
    findings = engine.run(CheckContext(book_id=1))
    assert len(findings) == 1
    assert findings[0].severity == "high"


def test_filter_intentional():
    f1 = Finding(category="a", description="keep")
    f2 = Finding(category="b", description="drop", is_intentional=True)
    f3 = Finding(category="c", description="drop2")
    filtered = filter_intentional([f1, f2, f3], {f3.key()})
    assert len(filtered) == 1
    assert filtered[0].category == "a"
