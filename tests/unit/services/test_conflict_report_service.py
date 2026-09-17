"""src/services/conflict_report_service.py の単体テスト."""


from src.services.conflict_report_service import (
    ConflictReportService, ConflictItem, ConflictReport,
)


class TestConflictItem:
    """ConflictItem dataclass のテスト."""

    def test_defaults(self):
        item = ConflictItem(category="deai", severity="low", title="t", description="d")
        assert item.field_path is None
        assert item.confidence == 1.0
        assert item.evidence_past == ""


class TestConflictReportService:
    """ConflictReportService のテスト."""

    def setup_method(self):
        self.service = ConflictReportService()

    def test_generate_report_empty(self):
        report = self.service.generate_conflict_report(book_id=1, ep_num=2, failed_audits=[])
        assert isinstance(report, ConflictReport)
        assert report.total_count == 0
        assert report.summary == "矛盾は検出されませんでした。"
        assert report.critical_count == 0

    def test_generate_report_single_audit(self):
        failed = [{"type": "deai", "feedback": "文体がAIっぽい"}]
        report = self.service.generate_conflict_report(book_id=1, ep_num=3, failed_audits=failed)
        assert report.total_count == 1
        assert report.book_id == 1
        assert report.ep_num == 3
        assert report.conflicts[0].title == "AI感・文体"
        assert report.conflicts[0].severity == "medium"

    def test_generate_report_severity_from_category(self):
        failed = [{"type": "causal_integrity", "feedback": "因果律が破綻"}]
        report = self.service.generate_conflict_report(1, 1, failed)
        assert report.conflicts[0].severity == "high"
        assert report.high_count == 1

    def test_generate_report_explicit_severity(self):
        failed = [{"type": "deai", "severity": "critical", "feedback": "致命的"}]
        report = self.service.generate_conflict_report(1, 1, failed)
        assert report.conflicts[0].severity == "critical"
        assert report.critical_count == 1

    def test_generate_report_unknown_type(self):
        failed = [{"type": "mystery_audit", "feedback": "不明な監査"}]
        report = self.service.generate_conflict_report(1, 1, failed)
        assert report.conflicts[0].severity == "medium"  # デフォルト
        assert report.conflicts[0].title == "mystery_audit"  # ラベル未定義はtypeそのまま

    def test_generate_report_multiple_with_counts(self):
        failed = [
            {"type": "deai", "severity": "critical", "feedback": "a"},
            {"type": "deai", "severity": "high", "feedback": "b"},
            {"type": "fast_screen", "feedback": "c"},
        ]
        report = self.service.generate_conflict_report(1, 5, failed)
        assert report.total_count == 3
        assert report.critical_count == 1
        assert report.high_count == 2
        assert report.medium_count == 0
        assert report.low_count == 0

    def test_generate_report_patch_review_id(self):
        report = self.service.generate_conflict_report(1, 1, [], patch_review_id=42)
        assert report.patch_review_id == 42

    def test_generate_report_bible_snapshot(self):
        failed = [{"type": "logical_consistency", "feedback": "magic_system に矛盾"}]
        snapshot = {"world_rules": {"magic_system": {"mana_cost": 10}}}
        report = self.service.generate_conflict_report(1, 1, failed, bible_snapshot=snapshot)
        assert report.conflicts[0].field_path == "logical_consistency.magic_system"

    def test_infer_field_path_hit(self):
        path = self.service._infer_field_path("deai", "tone が不自然", None)
        assert path == "deai.tone"

    def test_infer_field_path_miss(self):
        path = self.service._infer_field_path("deai", "関係ない記述", None)
        assert path is None

    def test_infer_field_path_unknown_type(self):
        path = self.service._infer_field_path("unknown", "text", None)
        assert path is None

    def test_extract_values_pattern1(self):
        current, suggested = self.service._extract_values(
            "x", "現在は10だが、20であるべき", None
        )
        assert current == "10"
        assert suggested == "20"

    def test_extract_values_no_match(self):
        current, suggested = self.service._extract_values("x", "パターンなし", None)
        assert current is None
        assert suggested is None

    def test_generate_summary_with_critical(self):
        conflicts = [
            ConflictItem(category="deai", severity="critical", title="t1", description="d1"),
            ConflictItem(category="deai", severity="high", title="t2", description="d2"),
        ]
        summary = self.service._generate_summary(conflicts)
        assert "合計 2 件" in summary
        assert "緊急対応" in summary

    def test_generate_unified_diff(self):
        diff = self.service.generate_unified_diff("line1\nline2\n", "line1\nchanged\n")
        assert "current" in diff
        assert "proposed" in diff
        assert "-line2" in diff
        assert "+changed" in diff

    def test_generate_unified_diff_identical(self):
        diff = self.service.generate_unified_diff("same\n", "same\n")
        assert diff == ""

    def test_generate_json_patch_add(self):
        patches = self.service.generate_json_patch({}, {"new": 1})
        assert patches == [{"op": "add", "path": "/new", "value": 1}]

    def test_generate_json_patch_remove(self):
        patches = self.service.generate_json_patch({"old": 1}, {})
        assert patches == [{"op": "remove", "path": "/old"}]

    def test_generate_json_patch_replace(self):
        patches = self.service.generate_json_patch({"k": 1}, {"k": 2})
        assert patches == [{"op": "replace", "path": "/k", "value": 2}]

    def test_generate_json_patch_no_change(self):
        patches = self.service.generate_json_patch({"k": 1}, {"k": 1})
        assert patches == []

    def test_to_dict_roundtrip(self):
        failed = [{"type": "deai", "feedback": "d"}]
        report = self.service.generate_conflict_report(7, 8, failed)
        d = self.service.to_dict(report)
        assert d["book_id"] == 7
        assert d["ep_num"] == 8
        assert d["total_count"] == 1
        assert d["conflicts"][0]["category"] == "deai"
        assert d["conflicts"][0]["confidence"] == 0.8
