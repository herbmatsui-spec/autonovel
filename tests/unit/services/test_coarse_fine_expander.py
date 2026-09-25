import pytest
from unittest.mock import AsyncMock, MagicMock
from src.services.default_plot_expander import DefaultPlotExpander
from src.models.plot import (
    EpisodeMacroSkeleton,
    PlotMacroBatch,
    PlotMicroBlueprint,
    MasterSceneBlock,
    PlotEpisode,
)


@pytest.fixture
def mock_repo():
    repo = MagicMock()
    repo.get_latest_bible = AsyncMock(return_value={"title": "テスト作品", "genre": "ファンタジー"})
    repo.get_plot = AsyncMock(return_value=None)
    repo.save_plot = AsyncMock(return_value=None)
    repo.get_characters = AsyncMock(return_value=[])
    repo.get_chapter = AsyncMock(return_value=None)
    return repo


@pytest.fixture
def mock_pm():
    pm = MagicMock()
    pm.build_macro_plot_skeleton_prompt = AsyncMock(return_value="macro prompt")
    pm.build_micro_scene_expander_prompt = AsyncMock(return_value="micro prompt")
    return pm


@pytest.fixture
def mock_llm():
    llm = MagicMock()
    return llm


class TestCoarseFineExpander:
    @pytest.mark.asyncio
    async def test_expand_macro_skeletons(self, mock_repo, mock_pm, mock_llm):
        batch = PlotMacroBatch(
            episodes=[
                EpisodeMacroSkeleton(ep_num=1, title="第1話"),
                EpisodeMacroSkeleton(ep_num=2, title="第2話"),
            ]
        )
        mock_res = MagicMock()
        mock_res.metadata = batch.model_dump()
        mock_llm.generate_json = AsyncMock(return_value=mock_res)

        expander = DefaultPlotExpander(mock_repo, mock_pm, mock_llm)
        skeletons = await expander.expand_macro_skeletons(book_id=1, target_ep_list=[1, 2])

        assert len(skeletons) == 2
        assert skeletons[0].ep_num == 1
        assert skeletons[1].ep_num == 2
        assert mock_repo.save_plot.call_count == 2

    @pytest.mark.asyncio
    async def test_expand_single_micro(self, mock_repo, mock_pm, mock_llm):
        micro_bp = PlotMicroBlueprint(
            ep_num=1,
            thought_process="演出思考",
            detailed_blueprint="2000字詳細フロー",
            scenes=[
                MasterSceneBlock(scene_number=1, action="導入"),
                MasterSceneBlock(scene_number=2, action="衝突"),
                MasterSceneBlock(scene_number=3, action="引き"),
            ],
        )
        mock_res = MagicMock()
        mock_res.metadata = micro_bp.model_dump()
        mock_llm.generate_json = AsyncMock(return_value=mock_res)

        expander = DefaultPlotExpander(mock_repo, mock_pm, mock_llm)
        skeleton = EpisodeMacroSkeleton(ep_num=1, title="骨子タイトル", tension=70)

        merged_plot = await expander.expand_single_micro(
            book_id=1,
            ep_num=1,
            skeleton=skeleton,
            previous_ending_text="前話のラストテキスト",
        )

        assert isinstance(merged_plot, PlotEpisode)
        assert merged_plot.ep_num == 1
        assert merged_plot.title == "骨子タイトル"
        assert merged_plot.tension == 70
        assert len(merged_plot.scenes) == 3
        assert mock_repo.save_plot.call_count == 1

    @pytest.mark.asyncio
    async def test_ensure_detailed_plot_cache_hit(self, mock_repo, mock_pm, mock_llm):
        # 既に3シーン展開済みのプロットが存在する場合、LLM呼び出しなしで即リターン
        existing = PlotEpisode(
            ep_num=1,
            title="既存プロット",
            scenes=[
                MasterSceneBlock(scene_number=1, action="導入"),
                MasterSceneBlock(scene_number=2, action="衝突"),
                MasterSceneBlock(scene_number=3, action="引き"),
            ],
        )
        mock_repo.get_plot = AsyncMock(return_value=existing)

        expander = DefaultPlotExpander(mock_repo, mock_pm, mock_llm)
        result = await expander.ensure_detailed_plot(book_id=1, ep_num=1)

        assert result.title == "既存プロット"
        assert mock_llm.generate_json.call_count == 0

    @pytest.mark.asyncio
    async def test_ensure_detailed_plot_idempotency(self, mock_repo, mock_pm, mock_llm):
        # 1回目は未展開でJIT展開、2回目はキャッシュヒット
        micro_bp = PlotMicroBlueprint(
            ep_num=1,
            scenes=[
                MasterSceneBlock(scene_number=1, action="導入"),
                MasterSceneBlock(scene_number=2, action="衝突"),
                MasterSceneBlock(scene_number=3, action="引き"),
            ],
        )
        mock_res = MagicMock()
        mock_res.metadata = micro_bp.model_dump()
        mock_llm.generate_json = AsyncMock(return_value=mock_res)

        expander = DefaultPlotExpander(mock_repo, mock_pm, mock_llm)

        # 1回目 (未展開)
        res1 = await expander.ensure_detailed_plot(book_id=1, ep_num=1)
        assert len(res1.scenes) == 3
        first_call_count = mock_llm.generate_json.call_count

        # 2回目用モック設定（保存されたプロットを返す）
        mock_repo.get_plot = AsyncMock(return_value=res1)

        # 2回目 (キャッシュヒット)
        res2 = await expander.ensure_detailed_plot(book_id=1, ep_num=1)
        assert res2.ep_num == 1
        # LLMの呼び出し回数が増えていないことを確認 (完全冪等)
        assert mock_llm.generate_json.call_count == first_call_count

    @pytest.mark.asyncio
    async def test_prefetch_next_episode_plot(self, mock_repo, mock_pm, mock_llm):
        existing = PlotEpisode(
            ep_num=2,
            scenes=[
                MasterSceneBlock(scene_number=1, action="導入"),
                MasterSceneBlock(scene_number=2, action="衝突"),
                MasterSceneBlock(scene_number=3, action="引き"),
            ],
        )
        mock_repo.get_plot = AsyncMock(return_value=existing)

        expander = DefaultPlotExpander(mock_repo, mock_pm, mock_llm)
        task = expander.prefetch_next_episode_plot(book_id=1, next_ep=2)
        assert task is not None
        await task
