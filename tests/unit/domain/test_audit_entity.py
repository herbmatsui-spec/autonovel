"""Audit entity (AuditFinding/AuditResult) の単体テスト."""

import pytest

from src.domain.entities.audit import (
    AuditFinding, AuditResult, AuditCategory, AuditSeverity, AuditStatus, AuditType,
)
from src.domain.value_objects.ids import NovelId, AuditId


class TestAuditFinding:
    """AuditFinding entity のテスト."""

    def test_create_factory(self):
        f = AuditFinding.create(
            category=AuditCategory.LOGIC, severity=AuditSeverity.HIGH,
            description="矛盾あり", episode_number=3,
            evidence_past="前話ではA", evidence_current="今話ではB",
        )
        assert f.status == AuditStatus.OPEN
        assert f.is_critical() is False

    def test_invalid_description(self):
        with pytest.raises(ValueError):
            AuditFinding.create(
                category=AuditCategory.LOGIC, severity=AuditSeverity.LOW,
                description="  ", episode_number=1,
            )

    def test_invalid_episode(self):
        with pytest.raises(ValueError):
            AuditFinding.create(
                category=AuditCategory.LOGIC, severity=AuditSeverity.LOW,
                description="x", episode_number=-1,
            )

    def test_lifecycle(self):
        f = AuditFinding.create(
            category=AuditCategory.STYLE, severity=AuditSeverity.MEDIUM,
            description="文体の乱れ", episode_number=2,
        )
        f.acknowledge()
        assert f.status == AuditStatus.ACKNOWLEDGED
        f.start_resolution()
        assert f.status == AuditStatus.IN_PROGRESS
        f.resolve("修正済み", "writer")
        assert f.status == AuditStatus.RESOLVED
        assert f.resolved_note == "修正済み"
        assert f.resolved_at is not None

    def test_reject_defer(self):
        f = AuditFinding.create(
            category=AuditCategory.PACING, severity=AuditSeverity.LOW,
            description="テンポ", episode_number=1,
        )
        f.reject("意図的")
        assert f.status == AuditStatus.REJECTED
        f2 = AuditFinding.create(
            category=AuditCategory.PACING, severity=AuditSeverity.LOW,
            description="テンポ2", episode_number=1,
        )
        f2.defer("後回し")
        assert f2.status == AuditStatus.DEFERRED

    def test_is_critical_and_is_open(self):
        f = AuditFinding.create(
            category=AuditCategory.PLOT_HOLE, severity=AuditSeverity.CRITICAL,
            description="重大欠陥", episode_number=5,
        )
        assert f.is_critical() is True
        assert f.is_open() is True
        f.resolve("done", "me")
        assert f.is_open() is False

    def test_to_dict(self):
        f = AuditFinding.create(
            category=AuditCategory.CONTINUITY, severity=AuditSeverity.INFO,
            description="軽微", episode_number=1,
        )
        d = f.to_dict()
        assert d["category"] == "continuity"
        assert d["severity"] == "info"
        assert d["status"] == "open"


class TestAuditResult:
    """AuditResult aggregate root のテスト."""

    def test_create_factory(self):
        r = AuditResult.create(
            novel_id=NovelId.generate(), episode_number=3, audit_type=AuditType.LOGICAL,
        )
        assert r.overall_score == 100
        assert r.findings == []

    def test_invalid_episode(self):
        with pytest.raises(ValueError):
            AuditResult.create(novel_id=NovelId.generate(), episode_number=0, audit_type=AuditType.QUICK)

    def test_add_finding_recalculates_score(self):
        novel_id = NovelId.generate()
        r = AuditResult.create(novel_id=novel_id, episode_number=2, audit_type=AuditType.COMPREHENSIVE)
        f = AuditFinding.create(
            category=AuditCategory.LOGIC, severity=AuditSeverity.CRITICAL,
            description="重大", episode_number=2,
        )
        r.add_finding(f)
        assert r.overall_score == 70  # 100 - 30

    def test_add_finding_episode_mismatch(self):
        novel_id = NovelId.generate()
        r = AuditResult.create(novel_id=novel_id, episode_number=2, audit_type=AuditType.LOGICAL)
        f = AuditFinding.create(
            category=AuditCategory.LOGIC, severity=AuditSeverity.LOW,
            description="x", episode_number=3,
        )
        with pytest.raises(ValueError):
            r.add_finding(f)

    def test_remove_finding(self):
        novel_id = NovelId.generate()
        r = AuditResult.create(novel_id=novel_id, episode_number=1, audit_type=AuditType.LOGICAL)
        f = AuditFinding.create(
            category=AuditCategory.LOGIC, severity=AuditSeverity.LOW,
            description="x", episode_number=1,
        )
        r.add_finding(f)
        assert r.overall_score == 97
        removed = r.remove_finding(f.id)
        assert removed is True
        assert r.overall_score == 100
        assert r.remove_finding(AuditId.generate()) is False

    def test_filters(self):
        novel_id = NovelId.generate()
        r = AuditResult.create(novel_id=novel_id, episode_number=1, audit_type=AuditType.COMPREHENSIVE)
        f_crit = AuditFinding.create(
            category=AuditCategory.LOGIC, severity=AuditSeverity.CRITICAL,
            description="c", episode_number=1,
        )
        f_low = AuditFinding.create(
            category=AuditCategory.STYLE, severity=AuditSeverity.LOW,
            description="s", episode_number=1,
        )
        r.add_finding(f_crit)
        r.add_finding(f_low)
        assert r.get_findings_by_category(AuditCategory.LOGIC) == [f_crit]
        assert r.get_findings_by_severity(AuditSeverity.LOW) == [f_low]
        assert len(r.get_open_findings()) == 2
        assert r.get_critical_findings() == [f_crit]

    def test_complete(self):
        novel_id = NovelId.generate()
        r = AuditResult.create(novel_id=novel_id, episode_number=1, audit_type=AuditType.LOGICAL)
        f = AuditFinding.create(
            category=AuditCategory.LOGIC, severity=AuditSeverity.MEDIUM,
            description="m", episode_number=1,
        )
        r.add_finding(f)
        r.complete("監査完了")
        assert r.summary == "監査完了"
        assert r.completed_at is not None
        assert r.overall_score == 92  # 100 - 8

    def test_to_dict(self):
        novel_id = NovelId.generate()
        r = AuditResult.create(novel_id=novel_id, episode_number=1, audit_type=AuditType.LOGICAL)
        d = r.to_dict()
        assert d["audit_type"] == "logical"
        assert d["episode_number"] == 1
        assert d["findings"] == []

    def test_eq_hash(self):
        novel_id = NovelId.generate()
        r1 = AuditResult.create(novel_id=novel_id, episode_number=1, audit_type=AuditType.LOGICAL)
        r2 = AuditResult.create(novel_id=novel_id, episode_number=1, audit_type=AuditType.LOGICAL)
        assert r1 != r2
        assert r1 != "not a result"
