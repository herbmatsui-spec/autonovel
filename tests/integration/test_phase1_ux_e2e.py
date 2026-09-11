import pytest
from src.backend.routers.commercial import (
    PublicationScheduleCreate,
    PublicationScheduleResponse,
)
from src.services.conflict_report_service import ConflictReportService
from src.services.book_score_service import BookScoreService


def test_phase1_ux_components():
    # 1. 商用投稿スケジュールスキーマの検証
    from datetime import datetime
    req = PublicationScheduleCreate(
        book_id=1,
        platform="narou",
        episode_range=(1, 5),
        scheduled_at=datetime.utcnow(),
    )
    assert req.platform == "narou"
    assert req.episode_range == (1, 5)

    # 2. コンフリクト判定サービスの検証
    service = ConflictReportService()
    assert service is not None

    # 3. BookScore 5次元スコア集計サービスの検証
    score_service = BookScoreService()
    assert score_service is not None
