"""上級者エディタ用データモデルの単体テスト."""
import pytest
from pydantic import ValidationError

from src.models.editor import (
    AssistAction,
    AssistRequest,
    AssistResponse,
    AskBibleRequest,
    AskBibleResponse,
    BeatCard,
    BranchType,
    ConsistencyAuditRequest,
    ConsistencyAuditResponse,
    ConsistencyIssue,
    GraphEvidenceNode,
    NextBeatsRequest,
    NextBeatsResponse,
    SensoryType,
    ToneType,
)


def test_sensory_and_tone_enums():
    """Enum値の定義確認"""
    assert SensoryType.VISUAL.value == "visual"
    assert SensoryType.AUDITORY.value == "auditory"
    assert SensoryType.OLFACTORY.value == "olfactory"
    assert SensoryType.TACTILE.value == "tactile"
    assert SensoryType.GUSTATORY.value == "gustatory"
    assert SensoryType.METAPHOR.value == "metaphor"

    assert ToneType.TENSION.value == "tension"
    assert ToneType.EROTIC.value == "erotic"
    assert ToneType.FAST_PACED.value == "fast_paced"


def test_assist_request_validation():
    """AssistRequest のバリデーション"""
    # 正常系
    req = AssistRequest(
        text="男は扉を開けた。",
        action=AssistAction.DESCRIBE,
        sensory_type=SensoryType.AUDITORY,
    )
    assert req.text == "男は扉を開けた。"
    assert req.action == AssistAction.DESCRIBE
    assert req.sensory_type == SensoryType.AUDITORY
    assert req.genre == "ハイファンタジー (R15)"

    # 異常系（空テキスト）
    with pytest.raises(ValidationError):
        AssistRequest(text="", action=AssistAction.DESCRIBE)


def test_assist_response():
    """AssistResponse のシリアライズ"""
    res = AssistResponse(
        original_text="男は扉を開けた。",
        result_text="重厚な鉄の扉が、軋んだ甲高い悲鳴を上げながらゆっくりと開かれた。",
        action=AssistAction.DESCRIBE,
        diff_summary="聴覚描写を追加",
    )
    assert res.action == AssistAction.DESCRIBE
    assert "軋んだ甲高い悲鳴" in res.result_text


def test_ask_bible_models():
    """AskBible 関連モデルのテスト"""
    node = GraphEvidenceNode(
        id="魔剣グラム",
        label="Item",
        properties={"attribute": "闇", "owner": "アルト"},
        source_reference="第2章",
    )
    req = AskBibleRequest(book_id=1, query="魔剣の能力を教えて")
    res = AskBibleResponse(
        answer="魔剣グラムは闇属性を帯びており、アルトが所有しています。",
        evidence_nodes=[node],
        related_characters=["アルト"],
    )

    assert req.book_id == 1
    assert res.evidence_nodes[0].id == "魔剣グラム"
    assert res.related_characters == ["アルト"]


def test_consistency_audit_models():
    """ConsistencyAudit 関連モデルのテスト"""
    issue = ConsistencyIssue(
        issue_type="attribute",
        severity="warning",
        description="前章で負傷した右腕で剣を振っています",
        conflicting_text="右手に持った剣を一閃した",
        suggested_fix="左手で短剣を構えるか、治療後の描写を挟んでください",
    )
    req = ConsistencyAuditRequest(book_id=1, content="アルトは右手に持った剣を一閃した")
    res = ConsistencyAuditResponse(
        has_issues=True,
        issues=[issue],
        confidence_score=0.95,
    )

    assert req.content.startswith("アルト")
    assert res.has_issues is True
    assert len(res.issues) == 1
    assert res.issues[0].severity == "warning"


def test_next_beats_models():
    """NextBeats 関連モデルのテスト"""
    card_a = BeatCard(
        card_id="card_a",
        branch_type=BranchType.ROYAL,
        title="王道の反撃",
        summary="アルトが魔剣を抜いて逆転の一撃を放つ",
        content="「ここまでだ！」アルトの抜いた魔剣が闇の刃となって敵を両断した。",
        hook_text="しかし、倒れた敵の背後から更なる影が迫る……",
    )
    req = NextBeatsRequest(book_id=1, current_text="敵に追い詰められたアルトは……")
    res = NextBeatsResponse(beats=[card_a], original_tail="敵に追い詰められたアルトは……")

    assert req.book_id == 1
    assert len(res.beats) == 1
    assert res.beats[0].branch_type == BranchType.ROYAL
