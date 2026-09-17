"""伏線自動注入〜回収〜整合性パイプラインの単体テスト。

Step 7 (format_unresolved_foreshadowings), Step 8 (detect_foreshadowing_mentions),
Step 9 (ForeshadowingService.check_and_resolve), Step 10 (audit_foreshadowings)
の統合テスト。
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.agents.context_builder_agent import ContextBuilderAgent
from src.services.foreshadowing_parser import detect_foreshadowing_mentions, ForeshadowingMention
from src.services.foreshadowing_service import ForeshadowingService
from src.services.auditors.foreshadowing_auditor import (
    audit_foreshadowings,
    validate_foreshadowing_order,
    ForeshadowingAuditResult,
)


# ── Step 7: format_unresolved_foreshadowings ──

class TestFormatUnresolvedForeshadowings:
    def test_empty_list(self):
        result = ContextBuilderAgent.format_unresolved_foreshadowings([])
        assert result == "なし"

    def test_dict_format(self):
        foreshadowings = [
            {"title": "謎の剣", "planted_episode": 3, "description": "主人公が見つけた剣", "target_episode": 10},
        ]
        result = ContextBuilderAgent.format_unresolved_foreshadowings(foreshadowings)
        assert "謎の剣" in result
        assert "第3話" in result
        assert "回収目標: 第10話" in result

    def test_object_format(self):
        mock_f = MagicMock()
        mock_f.title = "消えた手紙"
        mock_f.planted_episode = 5
        mock_f.description = "宛先不明の手紙"
        mock_f.target_episode = None
        result = ContextBuilderAgent.format_unresolved_foreshadowings([mock_f])
        assert "消えた手紙" in result
        assert "第5話" in result
        assert "回収目標" not in result  # target_episode=None


# ── Step 8: detect_foreshadowing_mentions ──

class TestDetectForeshadowingMentions:
    def test_detect_title_in_text(self):
        text = "太郎は謎の剣を手に取った。謎の剣は光を放った。"
        foreshadowings = [{"id": 1, "title": "謎の剣", "description": "主人公が見つけた剣"}]
        mentions = detect_foreshadowing_mentions(text, foreshadowings)
        assert len(mentions) == 1
        assert mentions[0].title == "謎の剣"
        assert mentions[0].mention_count == 2

    def test_detect_resolution_candidate(self):
        text = "ついに謎の剣の正体が明らかになった。"
        foreshadowings = [{"id": 1, "title": "謎の剣", "description": "主人公が見つけた剣"}]
        mentions = detect_foreshadowing_mentions(text, foreshadowings)
        assert len(mentions) == 1
        assert mentions[0].is_resolution_candidate is True

    def test_no_mention(self):
        text = "今日は平和な一日だった。"
        foreshadowings = [{"id": 1, "title": "謎の剣", "description": "主人公が見つけた剣"}]
        mentions = detect_foreshadowing_mentions(text, foreshadowings)
        assert len(mentions) == 0

    def test_empty_inputs(self):
        assert detect_foreshadowing_mentions("", []) == []
        assert detect_foreshadowing_mentions("テスト", []) == []
        assert detect_foreshadowing_mentions("", [{"id": 1, "title": "x"}]) == []


# ── Step 9: ForeshadowingService.check_and_resolve ──

class TestForeshadowingService:
    @pytest.mark.asyncio
    async def test_check_and_resolve_resolves_foreshadowing(self):
        """回収候補が検出された場合に resolve が呼ばれることを検証"""
        mock_f = MagicMock()
        mock_f.id = 1
        mock_f.title = "謎の剣"
        mock_f.description = "主人公が見つけた剣"
        mock_f.planted_episode = 3
        mock_f.target_episode = None
        mock_f.status = "planted"

        mock_repo = AsyncMock()
        mock_repo.get_unresolved.return_value = [mock_f]
        mock_repo.resolve.return_value = True

        service = ForeshadowingService(mock_repo)
        draft = "ついに謎の剣の正体が明らかになった。伝説の剣だったのだ。"
        resolved = await service.check_and_resolve(book_id=1, episode_num=10, draft_text=draft)

        assert "謎の剣" in resolved
        mock_repo.resolve.assert_awaited_once_with(1, 10)

    @pytest.mark.asyncio
    async def test_check_and_resolve_no_resolution(self):
        """回収キーワードがない場合は resolve されない"""
        mock_f = MagicMock()
        mock_f.id = 1
        mock_f.title = "謎の剣"
        mock_f.description = "主人公が見つけた剣"
        mock_f.planted_episode = 3
        mock_f.target_episode = None
        mock_f.status = "planted"

        mock_repo = AsyncMock()
        mock_repo.get_unresolved.return_value = [mock_f]

        service = ForeshadowingService(mock_repo)
        draft = "太郎は謎の剣を眺めていた。何も起きなかった。"
        resolved = await service.check_and_resolve(book_id=1, episode_num=10, draft_text=draft)

        assert resolved == []
        mock_repo.resolve.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_check_and_resolve_before_target(self):
        """回収目標話数に到達していない場合は progress に更新"""
        mock_f = MagicMock()
        mock_f.id = 1
        mock_f.title = "謎の剣"
        mock_f.description = "主人公が見つけた剣"
        mock_f.planted_episode = 3
        mock_f.target_episode = 20  # まだ遠い
        mock_f.status = "planted"

        mock_repo = AsyncMock()
        mock_repo.get_unresolved.return_value = [mock_f]
        mock_repo.progress.return_value = True

        service = ForeshadowingService(mock_repo)
        draft = "ついに謎の剣の正体が明らかになった。"
        resolved = await service.check_and_resolve(book_id=1, episode_num=10, draft_text=draft)

        assert resolved == []  # resolve はされない
        mock_repo.progress.assert_awaited_once_with(1)  # progress に更新


# ── Step 10: audit_foreshadowings ──

class TestForeshadowingAuditor:
    def test_validate_order_correct(self):
        assert validate_foreshadowing_order(3, 10) is True
        assert validate_foreshadowing_order(5, 5) is True

    def test_validate_order_violation(self):
        assert validate_foreshadowing_order(10, 3) is False

    def test_audit_clean(self):
        foreshadowings = [
            {"title": "謎の剣", "planted_episode": 3, "resolved_episode": 10, "status": "resolved"},
        ]
        result = audit_foreshadowings(foreshadowings, current_episode=15)
        assert result.is_valid is True
        assert result.total_issues == 0

    def test_audit_order_violation(self):
        foreshadowings = [
            {"title": "時空の裂け目", "planted_episode": 10, "resolved_episode": 3, "status": "resolved"},
        ]
        result = audit_foreshadowings(foreshadowings, current_episode=15)
        assert result.is_valid is False
        assert len(result.order_violations) == 1
        assert "順序矛盾" in result.order_violations[0]

    def test_audit_stale_warning(self):
        foreshadowings = [
            {"title": "忘れられた約束", "planted_episode": 1, "resolved_episode": None, "status": "planted"},
        ]
        result = audit_foreshadowings(foreshadowings, current_episode=20, stale_threshold=15)
        assert len(result.stale_warnings) >= 1
        assert "長期未回収" in result.stale_warnings[0]

    def test_audit_overdue(self):
        foreshadowings = [
            {"title": "封印の鍵", "planted_episode": 3, "resolved_episode": None,
             "status": "planted", "target_episode": 10},
        ]
        result = audit_foreshadowings(foreshadowings, current_episode=15)
        assert len(result.stale_warnings) >= 1
        assert "期限超過" in result.stale_warnings[-1]
