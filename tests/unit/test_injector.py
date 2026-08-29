"""tests/unit/test_injector.py"""
from src.consistency.findings import Finding, Evidence
from src.consistency.injector import format_findings_for_prompt, format_findings_compact


def test_format_findings_for_prompt():
    f1 = Finding(
        category="foreshadowing",
        severity="high",
        description="未回収の伏線: 魔王の再臨",
        suggestion="第12章で回収",
        evidence=[Evidence(source="第5章", text="我は再び蘇る")],
    )
    f2 = Finding(
        category="duplicate",
        severity="medium",
        description="第1章と第2章の類似度が35%",
    )
    out = format_findings_for_prompt([f1, f2])
    assert "[整合性チェック結果]" in out
    assert "FORSHADOWING" in out or "HIGH" in out
    assert "未回収の伏線" in out
    assert "提案: 第12章で回収" in out
    assert "証拠:" in out


def test_format_findings_compact():
    f = Finding(category="x", severity="low", description="short")
    out = format_findings_compact([f])
    assert "[LOW]" in out
    assert "short" in out


def test_format_findings_empty():
    assert format_findings_for_prompt([]) == ""
    assert format_findings_compact([]) == ""