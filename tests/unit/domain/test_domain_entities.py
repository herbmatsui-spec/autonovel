"""Domain entities (Novel/Chapter/Episode/Volume/Plot/PlotPoint/Arc) の単体テスト."""

import pytest
from datetime import datetime

from src.domain.entities.novel import Novel, Chapter, Episode, Volume
from src.domain.entities.plot import Plot, PlotPoint, Arc, PlotStatus, ChainPhase
from src.domain.value_objects.ids import NovelId, UserId, PlotId, ChapterId
from src.domain.value_objects.text import Title, MarkdownText, TextContent, Genre, Catchcopy, Summary
from src.domain.value_objects.metadata import NovelMode, NovelStatus
from src.domain.value_objects.scores import TensionScore, CostScore


class TestNovelEntity:
    """Novel aggregate root のテスト."""

    def test_create_factory(self):
        user_id = UserId.generate()
        novel = Novel.create(title="テスト作品", author_id=user_id, genre="fantasy")
        assert isinstance(novel.id, NovelId)
        assert novel.title.value == "テスト作品"
        assert novel.status == NovelStatus.DRAFT
        assert novel.mode == NovelMode.EASY
        assert novel.target_episodes == 50
        assert novel.cumulative_tension == 0
        assert novel.sanctuary_integrity == 100

    def test_update_metadata_title(self):
        novel = Novel.create(title="旧タイトル", author_id=UserId.generate())
        novel.update_metadata(title="新タイトル")
        assert novel.title.value == "新タイトル"

    def test_update_metadata_target_episodes_invalid(self):
        novel = Novel.create(title="t", author_id=UserId.generate())
        with pytest.raises(ValueError):
            novel.update_metadata(target_episodes=0)

    def test_change_status(self):
        novel = Novel.create(title="t", author_id=UserId.generate())
        novel.change_status(NovelStatus.PUBLISHED)
        assert novel.status == NovelStatus.PUBLISHED

    def test_set_mode(self):
        novel = Novel.create(title="t", author_id=UserId.generate())
        novel.set_mode(NovelMode.EXPERT)
        assert novel.mode == NovelMode.EXPERT

    def test_add_tension(self):
        novel = Novel.create(title="t", author_id=UserId.generate())
        novel.add_tension(30)
        assert novel.cumulative_tension == 30

    def test_add_qol(self):
        novel = Novel.create(title="t", author_id=UserId.generate())
        novel.add_qol(10)
        assert novel.cumulative_qol == 10

    def test_add_cost(self):
        novel = Novel.create(title="t", author_id=UserId.generate())
        novel.add_cost(0.5, tokens=1000)
        assert novel.cumulative_cost.value == pytest.approx(0.5)
        assert novel.cumulative_cost.tokens_used == 1000

    def test_update_sanctuary_integrity(self):
        novel = Novel.create(title="t", author_id=UserId.generate())
        novel.update_sanctuary_integrity(80)
        assert novel.sanctuary_integrity == 80

    def test_update_sanctuary_integrity_invalid(self):
        novel = Novel.create(title="t", author_id=UserId.generate())
        with pytest.raises(ValueError):
            novel.update_sanctuary_integrity(101)

    def test_set_current_branch(self):
        novel = Novel.create(title="t", author_id=UserId.generate())
        branch_id = NovelId.generate()
        novel.set_current_branch(branch_id)
        assert novel.current_branch_id == branch_id

    def test_to_metadata(self):
        novel = Novel.create(title="t", author_id=UserId.generate())
        metadata = novel.to_metadata()
        assert metadata.novel_id == novel.id
        assert metadata.title.value == "t"

    def test_eq_hash(self):
        user_id = UserId.generate()
        n1 = Novel.create(title="a", author_id=user_id)
        # copy with same id
        n2 = Novel(
            id=n1.id, title=Title("b"), author_id=user_id, genre=Genre(""),
            catchcopy=Catchcopy(""), synopsis=Summary(""), concept=Summary(""),
        )
        assert n1 == n2
        assert hash(n1) == hash(n2)
        assert n1 != "not a novel"


class TestChapterEntity:
    """Chapter entity のテスト."""

    def test_create_factory(self):
        novel_id = NovelId.generate()
        branch_id = NovelId.generate()
        ch = Chapter.create(novel_id=novel_id, branch_id=branch_id, episode_number=3, title="第3話")
        assert ch.episode_number == 3
        assert ch.title.value == "第3話"
        assert ch.content == ""

    def test_create_invalid_episode(self):
        with pytest.raises(ValueError):
            Chapter.create(novel_id=NovelId.generate(), branch_id=NovelId.generate(), episode_number=0, title="x")

    def test_update_content_immutable(self):
        novel_id = NovelId.generate()
        branch_id = NovelId.generate()
        ch = Chapter.create(novel_id=novel_id, branch_id=branch_id, episode_number=1, title="t")
        ch2 = ch.update_content("本文です")
        assert ch2.content == "本文です"
        assert ch.content == ""  # 元は不変

    def test_set_score_immutable(self):
        novel_id = NovelId.generate()
        branch_id = NovelId.generate()
        ch = Chapter.create(novel_id=novel_id, branch_id=branch_id, episode_number=1, title="t")
        ch2 = ch.set_score(75)
        assert ch2.score_story == 75
        assert ch.score_story is None

    def test_eq_hash(self):
        novel_id = NovelId.generate()
        branch_id = NovelId.generate()
        c1 = Chapter.create(novel_id=novel_id, branch_id=branch_id, episode_number=1, title="a")
        c2 = c1.update_content("x")
        assert c1 == c2
        assert hash(c1) == hash(c2)


class TestEpisodeEntity:
    """Episode entity のテスト."""

    def test_create_factory(self):
        ep = Episode.create(novel_id=NovelId.generate(), branch_id=NovelId.generate(), number=2, title="第二話")
        assert ep.number == 2
        assert ep.tension == 50

    def test_create_invalid_number(self):
        with pytest.raises(ValueError):
            Episode.create(novel_id=NovelId.generate(), branch_id=NovelId.generate(), number=0, title="x")


class TestVolumeEntity:
    """Volume entity のテスト."""

    def test_valid(self):
        v = Volume(
            id=NovelId.generate(), novel_id=NovelId.generate(), number=1,
            title=Title("第一巻"), start_episode=1, end_episode=10,
        )
        assert v.number == 1

    def test_invalid_number(self):
        with pytest.raises(ValueError):
            Volume(
                id=NovelId.generate(), novel_id=NovelId.generate(), number=0,
                title=Title("x"), start_episode=1, end_episode=10,
            )

    def test_invalid_range(self):
        with pytest.raises(ValueError):
            Volume(
                id=NovelId.generate(), novel_id=NovelId.generate(), number=1,
                title=Title("x"), start_episode=5, end_episode=1,
            )


class TestPlotEntity:
    """Plot entity のテスト."""

    def test_create_factory(self):
        novel_id = NovelId.generate()
        branch_id = NovelId.generate()
        plot = Plot.create(novel_id=novel_id, branch_id=branch_id, episode_number=5, title="第5話プロット")
        assert plot.episode_number == 5
        assert plot.tension_score.value == 50
        assert plot.status == PlotStatus.PLANNED
        assert plot.current_chain_phase == ChainPhase.FRICITON

    def test_create_invalid_episode(self):
        with pytest.raises(ValueError):
            Plot.create(novel_id=NovelId.generate(), branch_id=NovelId.generate(), episode_number=0, title="x")

    def test_update_content(self):
        plot = Plot.create(novel_id=NovelId.generate(), branch_id=NovelId.generate(), episode_number=1, title="t")
        plot.update_content(title="新しいタイトル", summary="あらすじ", one_line_summary="一行")
        assert plot.title.value == "新しいタイトル"
        assert plot.summary.content == "あらすじ"
        assert plot.one_line_summary == "一行"

    def test_set_tension(self):
        plot = Plot.create(novel_id=NovelId.generate(), branch_id=NovelId.generate(), episode_number=1, title="t")
        plot.set_tension(85, delta=30)
        assert plot.tension_score.value == 85
        assert plot.tension_score.delta == 30
        assert plot.tension_score.is_catharsis()

    def test_set_catharsis(self):
        plot = Plot.create(novel_id=NovelId.generate(), branch_id=NovelId.generate(), episode_number=1, title="t")
        plot.set_catharsis(90, catharsis_type="大カタルシス")
        assert plot.catharsis == 90
        assert plot.catharsis_type == "大カタルシス"
        assert plot.is_catharsis is True

    def test_set_catharsis_without_type(self):
        plot = Plot.create(novel_id=NovelId.generate(), branch_id=NovelId.generate(), episode_number=1, title="t")
        plot.set_catharsis(50)
        assert plot.catharsis == 50
        assert plot.is_catharsis is False

    def test_lock_unlock(self):
        plot = Plot.create(novel_id=NovelId.generate(), branch_id=NovelId.generate(), episode_number=1, title="t")
        plot.lock()
        assert plot.is_locked is True
        plot.unlock()
        assert plot.is_locked is False

    def test_add_remove_scene(self):
        plot = Plot.create(novel_id=NovelId.generate(), branch_id=NovelId.generate(), episode_number=1, title="t")
        plot.add_scene("戦闘シーン")
        plot.add_scene("日常シーン")
        assert plot.scenes == ["戦闘シーン", "日常シーン"]
        assert plot.remove_scene(0) is True
        assert plot.scenes == ["日常シーン"]
        assert plot.remove_scene(99) is False

    def test_update_scores_clamped(self):
        plot = Plot.create(novel_id=NovelId.generate(), branch_id=NovelId.generate(), episode_number=1, title="t")
        plot.update_scores(state_integrity=150, emotional_resonance=-10, thematic_depth=50, literary_beauty=80)
        assert plot.state_integrity_score == 100
        assert plot.emotional_resonance_score == 0
        assert plot.thematic_depth_score == 50

    def test_add_healed_field(self):
        plot = Plot.create(novel_id=NovelId.generate(), branch_id=NovelId.generate(), episode_number=1, title="t")
        plot.add_healed_field("tension")
        plot.add_healed_field("tension")  # 重複は追加されない
        assert plot.healed_fields == ["tension"]

    def test_to_dict_roundtrip_fields(self):
        novel_id = NovelId.generate()
        branch_id = NovelId.generate()
        plot = Plot.create(novel_id=novel_id, branch_id=branch_id, episode_number=2, title="第2話")
        plot.set_tension(70, delta=10)
        d = plot.to_dict()
        assert d["episode_number"] == 2
        assert d["title"] == "第2話"
        assert d["tension"] == 70
        assert d["tension_delta"] == 10
        assert d["status"] == "planned"
        assert d["current_chain_phase"] == "Friction"

    def test_eq_hash(self):
        novel_id = NovelId.generate()
        branch_id = NovelId.generate()
        p1 = Plot.create(novel_id=novel_id, branch_id=branch_id, episode_number=1, title="a")
        p2 = Plot.create(novel_id=novel_id, branch_id=branch_id, episode_number=1, title="b")
        assert p1 != p2  # idが異なる
        assert p1 != "not a plot"


class TestPlotPointEntity:
    """PlotPoint entity のテスト."""

    def test_valid(self):
        pp = PlotPoint(
            id=PlotId.generate(), plot_id=PlotId.generate(), order=1,
            description=TextContent("対立点"), type="conflict", tension_contribution=10,
        )
        assert pp.order == 1

    def test_invalid_order(self):
        with pytest.raises(ValueError):
            PlotPoint(
                id=PlotId.generate(), plot_id=PlotId.generate(), order=-1,
                description=TextContent("x"), type="setup",
            )


class TestArcEntity:
    """Arc entity のテスト."""

    def test_create_factory(self):
        arc = Arc.create(
            novel_id=NovelId.generate(), name="序章アーク",
            description=MarkdownText("説明"), start_episode=1, end_episode=10,
        )
        assert arc.get_span() == 10
        assert arc.status == PlotStatus.PLANNED

    def test_invalid_name(self):
        with pytest.raises(ValueError):
            Arc.create(novel_id=NovelId.generate(), name="", description=MarkdownText(""), start_episode=1, end_episode=2)

    def test_invalid_start(self):
        with pytest.raises(ValueError):
            Arc.create(novel_id=NovelId.generate(), name="a", description=MarkdownText(""), start_episode=0, end_episode=2)

    def test_invalid_range(self):
        with pytest.raises(ValueError):
            Arc.create(novel_id=NovelId.generate(), name="a", description=MarkdownText(""), start_episode=5, end_episode=1)

    def test_contains_episode(self):
        arc = Arc.create(novel_id=NovelId.generate(), name="a", description=MarkdownText(""), start_episode=3, end_episode=8)
        assert arc.contains_episode(3) is True
        assert arc.contains_episode(8) is True
        assert arc.contains_episode(2) is False
        assert arc.contains_episode(9) is False


# 便利なエイリアス import（テスト内参照用）
from src.domain.value_objects.text import Genre, Catchcopy, Summary  # noqa: E402
from src.domain.value_objects.metadata import NovelMode  # noqa: E402
