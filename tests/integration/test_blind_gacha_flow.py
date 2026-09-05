# tests/integration/test_blind_gacha_flow.py
"""Integration tests for Blind Peer Review in GachaService."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.domain.entities.easy_mode import GachaPlanType, GachaRequest
from src.services.blind_review import BlindReviewGate
from src.services.gacha_service import GachaService


@pytest.mark.asyncio
async def test_blind_gacha_generation_and_evaluation():
    """Verify that GachaService generates 3 plans, scrubs competitor proposals, and independently scores each."""
    mock_llm = MagicMock()
    # Mock json generation for 3 proposals
    mock_llm.generate_json = AsyncMock(
        side_effect=[
            {
                "story_content": {
                    "title": "王道：勇者覚醒の道",
                    "logline": "平穏な村を追われた少年が伝説の聖剣に選ばれ世界を救う旅に出る。",
                    "protagonist_summary": "純粋で正義感の強い少年アレン",
                    "charm_point": "圧倒的な努力と覚醒による爽快なカタルシス展開",
                }
            },
            {
                "story_content": {
                    "title": "変化球：魔王が勇者の教育係",
                    "logline": "魔王が身分を隠して冴えない勇者を一人前に育成する異色のコメディ。",
                    "protagonist_summary": "苦労性の引退間近な魔王",
                    "charm_point": "敵味方の立場逆転とユーモア溢れる掛け合い",
                }
            },
            {
                "story_content": {
                    "title": "ダーク：復讐の使徒",
                    "logline": "全てを裏切られた元聖騎士が闇の力を手にして復讐を遂行する。",
                    "protagonist_summary": "冷徹で目的のためには手段を選ばない男",
                    "charm_point": "容赦ない復讐劇と心理的サスペンスの深み",
                }
            },
        ]
    )

    mock_db = MagicMock()
    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_db.get_session = MagicMock()
    mock_db.get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_db.get_session.return_value.__aexit__ = AsyncMock()

    mock_event_bus = MagicMock()
    mock_event_bus.publish_blind = AsyncMock()

    gate = BlindReviewGate(
        forbidden_agents=["proposal_other", "plan_other"],
        mode="scrub",
    )

    service = GachaService(
        llm_service=mock_llm,
        db=mock_db,
        blind_gate=gate,
        event_bus=mock_event_bus,
    )

    request = GachaRequest(
        genre="fantasy",
        keywords=["勇者", "魔法", "成長"],
        temperature=0.7,
    )

    response = await service.generate_plans(request)

    # 1. Verify 3 plans returned
    assert len(response.plans) == 3
    plan_types = {p.plan_type for p in response.plans}
    assert plan_types == {GachaPlanType.ROYAL, GachaPlanType.CURVEBALL, GachaPlanType.DARK}

    # 2. Verify all plans received blind audit scores
    for plan in response.plans:
        assert plan.audit_score is not None
        assert 70.0 <= plan.audit_score <= 100.0
        assert plan.critique is not None
        assert plan.recommendation_reason is not None

    # 3. Verify exactly one recommended plan
    recommended = [p for p in response.plans if p.is_recommended]
    assert len(recommended) == 1
    assert response.recommended_plan_id == recommended[0].plan_id

    # 4. Verify publish_blind was dispatched through event bus
    assert mock_event_bus.publish_blind.called
    assert gate.blocked_count >= 3  # BlindReviewGate successfully scrubbed competing plans
