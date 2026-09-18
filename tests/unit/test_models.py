from src.models.unified_audit import ConflictItemSchema, QualitativeAudit, UnifiedAuditReport

def test_conflict_item_schema():
    item = ConflictItemSchema(
        category="rhythm",
        severity="high",
        title="文長が長すぎます",
        description="一文が120文字を超えています。",
        field_path="paragraph_1",
        current_value="長文...",
        suggested_value="短文...",
    )
    assert item.category == "rhythm"
    assert item.severity == "high"
    assert item.confidence == 0.9

def test_unified_audit_report_with_conflicts():
    qual = QualitativeAudit(
        hook_score=80.0,
        emotional_score=75.0,
        character_consistency=85.0,
        overall_score=80.0,
        critique="良好な導入です",
    )
    conflict = ConflictItemSchema(
        category="dialogue",
        severity="medium",
        title="台詞率低下",
        description="台詞比率が低すぎます",
    )
    report = UnifiedAuditReport(
        is_acceptable=True,
        final_score=82.5,
        quantitative_score=85.0,
        qualitative=qual,
        detected_cliches=["王道"],
        dialogue_ratio=0.15,
        conflicts=[conflict],
    )
    assert report.is_acceptable is True
    assert len(report.conflicts) == 1
    assert report.conflicts[0].category == "dialogue"
