"""
Regression tests for Step 11: PDCA Controller and Audit Pipeline integration into WritingCoordinator.
Verifies that:
1. WritingCoordinator initializes with default PDCAController, AuditPipeline, and LocalPolisher.
2. Full text regeneration loop is skipped when PDCA controller says should_regenerate_full_text() is False.
3. Single-shot local polish is applied when audit issues exist with location and suggestion.
4. Local patch count is tracked and limited to single-shot per PDCA policy.
"""

from unittest.mock import MagicMock, AsyncMock
import pytest
from src.audit.unified_llm_auditor import Issue as AuditIssue
from src.domain.writing.coordinator import WritingCoordinator
from src.generation.pdca_controller import PDCAController


class DummyEpisode:
    def __init__(self, content: str):
        self.content = content


@pytest.mark.asyncio
async def test_writing_coordinator_pdca_skips_full_regeneration_and_applies_single_patch():
    # Mock dependencies
    mock_writer = MagicMock()
    mock_writer.generate_episodes = AsyncMock(return_value=500)
    mock_repo = MagicMock()
    mock_score_calculator = MagicMock()
    mock_score_calculator.calculate_score = AsyncMock()

    dummy_ep = DummyEpisode("昔々ある所に、お爺さんとお婆さんが住んでいました。毎日平和でした。")
    mock_repo.get_episode_by_number.return_value = dummy_ep

    mock_audit = MagicMock()
    # Issue with location and suggestion
    mock_audit.run.return_value = [
        AuditIssue(
            type="weak_conflict",
            message="葛藤が弱いです",
            location=(15, 30),
            suggestion="もっと劇的な事件を起こしてください",
        )
    ]

    mock_polisher = MagicMock()
    mock_polisher.polish.return_value = "昔々ある所に、波乱万丈なお爺さんとお婆さんが住んでいました。毎日事件の連続でした。"

    # PDCA with max_regenerations=0 (default) and max_local_patches=1
    pdca = PDCAController(max_regenerations=0, max_local_patches=1)

    coordinator = WritingCoordinator(
        writer=mock_writer,
        repo=mock_repo,
        book_score_calculator=mock_score_calculator,
        pdca_controller=pdca,
        audit_pipeline=mock_audit,
        local_polisher=mock_polisher,
    )

    reporter = MagicMock()

    # Execute auto_regenerate flow with start_ep=1, end_ep=1
    word_count = await coordinator.generate_episodes(
        book_id=1,
        start_ep=1,
        end_ep=1,
        passion=1.0,
        target_word_count=500,
        is_easy_mode=True,
        reporter=reporter,
        branch_id=1,
        auto_regenerate=True,
        max_retries=3,
    )

    # 1. Full text regeneration score calculation was NEVER called (skipped)
    mock_score_calculator.calculate_score.assert_not_called()

    # 2. Audit pipeline was executed on the episode text
    mock_audit.run.assert_called_once_with("昔々ある所に、お爺さんとお婆さんが住んでいました。毎日平和でした。")

    # 3. Local polisher was invoked for single-shot improvement
    mock_polisher.polish.assert_called_once_with(
        text="昔々ある所に、お爺さんとお婆さんが住んでいました。毎日平和でした。",
        target_range=(15, 30),
        improvement_instruction="もっと劇的な事件を起こしてください",
    )

    # 4. Episode was updated and saved
    assert dummy_ep.content == "昔々ある所に、波乱万丈なお爺さんとお婆さんが住んでいました。毎日事件の連続でした。"
    mock_repo.save_episode.assert_called_once_with(dummy_ep)

    # 5. PDCA recorded the local patch
    assert pdca.local_patch_count == 1
    assert not pdca.can_do_local_patch()

    # 6. Word count returned intact
    assert word_count == 500


@pytest.mark.asyncio
async def test_writing_coordinator_pdca_no_patch_when_limit_reached():
    mock_writer = MagicMock()
    mock_writer.generate_episodes = AsyncMock(return_value=200)
    mock_repo = MagicMock()
    dummy_ep = DummyEpisode("テキスト内容")
    mock_repo.get_episode_by_number.return_value = dummy_ep

    mock_audit = MagicMock()
    mock_audit.run.return_value = [
        AuditIssue(
            type="weak_conflict",
            message="葛藤不足",
            location=(0, 5),
            suggestion="修正指示",
        )
    ]
    mock_polisher = MagicMock()

    # PDCA with local patches already exhausted
    pdca = PDCAController(max_regenerations=0, max_local_patches=1)
    pdca.record_local_patch()  # 1 of 1 used

    coordinator = WritingCoordinator(
        writer=mock_writer,
        repo=mock_repo,
        book_score_calculator=MagicMock(),
        pdca_controller=pdca,
        audit_pipeline=mock_audit,
        local_polisher=mock_polisher,
    )

    await coordinator.generate_episodes(
        book_id=1,
        start_ep=1,
        end_ep=1,
        passion=1.0,
        target_word_count=200,
        is_easy_mode=True,
        reporter=None,
        branch_id=1,
        auto_regenerate=True,
    )

    # Audit pipeline and polisher should not even be called
    mock_audit.run.assert_not_called()
    mock_polisher.polish.assert_not_called()
    mock_repo.save_episode.assert_not_called()
