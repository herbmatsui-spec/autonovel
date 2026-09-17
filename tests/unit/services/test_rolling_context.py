"""3層ローリング記憶およびエピソードダイジェストの単体テスト (v5.0 Step 13〜17)."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.backend.database.models_digest import EpisodeDigestModel
from src.services.context_compression.digest_service import (
    generate_episode_digest,
    EpisodeDigestRepository,
    EpisodeDigestService,
    MAX_DIGEST_LENGTH,
)
from src.services.context_compression.rolling_memory import RollingMemoryBuilder


# ── Step 13: EpisodeDigestModel ──

class TestEpisodeDigestModel:
    def test_model_instantiation(self):
        digest = EpisodeDigestModel(
            book_id=1,
            episode_num=5,
            digest_text="太郎は謎の洞窟で古文書を手に入れた。",
        )
        assert digest.__tablename__ == "episode_digests"
        assert digest.book_id == 1
        assert digest.episode_num == 5
        assert "古文書" in digest.digest_text
        assert repr(digest).startswith("<EpisodeDigest")


# ── Step 14: generate_episode_digest & EpisodeDigestService ──

class TestEpisodeDigestService:
    @pytest.mark.asyncio
    async def test_generate_episode_digest_with_mock_llm(self):
        mock_llm = AsyncMock()
        mock_llm.generate.return_value = "・太郎が宝箱を開けた。\n・伝説の短剣を入手した。"

        draft = "長い戦闘の末、太郎はついに宝箱の前に立った。鍵を回すと中から短剣が現れた。"
        digest = await generate_episode_digest(mock_llm, draft, ep_num=3)

        assert "太郎" in digest
        assert len(digest) <= MAX_DIGEST_LENGTH

    @pytest.mark.asyncio
    async def test_generate_episode_digest_fallback_when_llm_none(self):
        draft = (
            "村を出発した。\n"
            "森の中でオオカミに襲われたが撃退した。\n"
            "夜になり安全な小屋に到着した。"
        )
        digest = await generate_episode_digest(None, draft, ep_num=1)
        assert "第1話要約" in digest
        assert "小屋に到着した" in digest
        assert len(digest) <= MAX_DIGEST_LENGTH

    @pytest.mark.asyncio
    async def test_generate_episode_digest_empty_draft(self):
        digest = await generate_episode_digest(None, "", ep_num=2)
        assert "特筆すべき出来事なし" in digest

    @pytest.mark.asyncio
    async def test_episode_digest_repository_save_and_get(self):
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_session.execute.return_value = mock_result

        repo = EpisodeDigestRepository(mock_session)
        digest = await repo.save_digest(book_id=10, episode_num=1, digest_text="第1話の事実要約")

        assert digest.book_id == 10
        assert digest.episode_num == 1
        mock_session.add.assert_called_once()
        mock_session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_episode_digest_service_summarize_and_save(self):
        mock_repo = AsyncMock()
        mock_llm = AsyncMock()
        mock_llm.generate.return_value = "敵将を討ち取った。"

        service = EpisodeDigestService(repo=mock_repo, llm=mock_llm)
        res = await service.summarize_and_save(book_id=1, episode_num=7, draft_text="激しい戦いの末...")

        assert "敵将を討ち取った" in res
        mock_repo.save_digest.assert_awaited_once_with(
            book_id=1,
            episode_num=7,
            digest_text="敵将を討ち取った。",
        )


# ── Step 15 & 16: RollingMemoryBuilder ──

class TestRollingMemoryBuilder:
    def test_build_context_structure(self):
        builder = RollingMemoryBuilder()
        bible = "世界名: エルドラシア。主人公: 太郎（魔法剣士）。"
        digests = [
            "第1話: 太郎が旅立つ。",
            "第2話: 謎の魔術師に出会う。",
        ]
        prev_text = "太郎は森を抜けて次の街へ向かっていた。"

        ctx = builder.build_context(
            bible_summary=bible,
            past_digests=digests,
            prev_episode_text=prev_text,
        )

        assert "【設定・世界観バイブル】" in ctx
        assert "エルドラシア" in ctx
        assert "【過去話の確定事実タイムライン】" in ctx
        assert "第1話: 太郎が旅立つ。" in ctx
        assert "第2話: 謎の魔術師に出会う。" in ctx
        assert "【直前エピソード本文】" in ctx
        assert "森を抜けて" in ctx

    def test_build_context_with_digest_models(self):
        builder = RollingMemoryBuilder()
        model1 = EpisodeDigestModel(book_id=1, episode_num=1, digest_text="剣を拾う")
        model2 = EpisodeDigestModel(book_id=1, episode_num=2, digest_text="城へ向かう")

        ctx = builder.build_context(
            bible_summary="基本設定",
            past_digests=[model1, model2],
            prev_episode_text="城の前に到着した。",
        )

        assert "第1話: 剣を拾う" in ctx
        assert "第2話: 城へ向かう" in ctx

    def test_window_control_under_max(self):
        builder = RollingMemoryBuilder(max_recent_digests=10)
        digests = [f"第{i}話の事実" for i in range(1, 6)]
        windowed = builder.filter_and_window_digests(digests)
        assert len(windowed) == 5

    def test_window_control_exceeding_max(self):
        # 50話分ある場合、最初の2話 + 省略マーカー + 直近(10-2)=8話 ＝ 計11行
        builder = RollingMemoryBuilder(max_recent_digests=10, preserve_initial_digests=2)
        digests = [f"第{i}話の事実" for i in range(1, 51)]
        windowed = builder.filter_and_window_digests(digests)

        assert len(windowed) == 11
        assert "第1話の事実" in windowed[0]
        assert "第2話の事実" in windowed[1]
        assert "省略" in windowed[2]
        assert "第50話の事実" in windowed[-1]

    def test_truncate_prev_episode(self):
        builder = RollingMemoryBuilder(max_prev_episode_chars=100)
        long_text = "あ" * 300
        res = builder.truncate_prev_episode(long_text)
        assert "前略" in res
        assert len(res) < 150

    def test_estimate_tokens_and_stats(self):
        builder = RollingMemoryBuilder()
        stats = builder.get_context_stats(
            bible_summary="世界観テキスト",
            past_digests=["第1話事実", "第2話事実"],
            prev_episode_text="直前の文章",
        )
        assert stats["total_chars"] > 0
        assert stats["estimated_tokens"] > 0
        assert stats["past_digests_count_raw"] == 2
        assert stats["past_digests_count_windowed"] == 2
