"""Value objects (ids/text/scores/metadata) の単体テスト."""

import pytest
from uuid import UUID

from src.domain.value_objects.ids import (
    NovelId, ChapterId, EpisodeId, CharacterId, BranchId, PlotId,
    SettingId, LoreId, PlotPointId, ArcId, AuditId, UserId,
)
from src.domain.value_objects.text import (
    TextFormat, TextContent, PlainText, MarkdownText, HtmlText,
    Title, Summary, Catchcopy, Genre,
)
from src.domain.value_objects.scores import (
    QualityScore, TensionScore, BookScore, QolScore, CostScore,
)
from src.domain.value_objects.metadata import (
    NovelStatus, NovelMode, SettingType, NovelMetadata,
    PublishPlatform, PublishStatus, PublishMetadata,
    ChapterMetadata, CharacterMetadata, BranchMetadata, AuditMetadata,
)


class TestIdValueObjects:
    """ID value objects のテスト."""

    def test_novel_id(self):
        nid = NovelId.generate()
        assert isinstance(nid.value, UUID)
        nid2 = NovelId.from_string(str(nid))
        assert nid == nid2
        assert str(nid) == str(nid.value)

    def test_chapter_id(self):
        cid = ChapterId.generate()
        assert ChapterId.from_string(str(cid)) == cid

    def test_episode_id(self):
        eid = EpisodeId.from_int(5)
        assert eid.value == 5
        assert int(eid) == 5
        with pytest.raises(ValueError):
            EpisodeId.from_int(0)

    def test_character_id(self):
        x = CharacterId.generate()
        assert CharacterId.from_string(str(x)) == x

    def test_branch_id(self):
        x = BranchId.generate()
        assert BranchId.from_string(str(x)) == x

    def test_plot_id(self):
        x = PlotId.generate()
        assert PlotId.from_string(str(x)) == x

    def test_setting_id(self):
        x = SettingId.generate()
        assert SettingId.from_string(str(x)) == x

    def test_lore_id(self):
        x = LoreId.generate()
        assert LoreId.from_string(str(x)) == x

    def test_plot_point_id(self):
        x = PlotPointId.generate()
        assert PlotPointId.from_string(str(x)) == x

    def test_arc_id(self):
        x = ArcId.generate()
        assert ArcId.from_string(str(x)) == x

    def test_audit_id(self):
        x = AuditId.generate()
        assert AuditId.from_string(str(x)) == x

    def test_user_id(self):
        x = UserId.generate()
        assert UserId.from_string(str(x)) == x


class TestTextContentVO:
    """TextContent value objects のテスト."""

    def test_textcontent_basic(self):
        tc = TextContent("テスト", format=TextFormat.MARKDOWN)
        assert tc.word_count() == 1
        assert tc.char_count() == 3
        assert tc.is_empty() is False
        assert len(tc) == 3

    def test_textcontent_empty(self):
        tc = TextContent("  ")
        assert tc.is_empty() is True

    def test_textcontent_add(self):
        a = TextContent("abc")
        b = TextContent("def")
        c = a + b
        assert c.content == "abcdef"

    def test_textcontent_add_format_mismatch(self):
        a = TextContent("abc", format=TextFormat.MARKDOWN)
        b = TextContent("def", format=TextFormat.HTML)
        c = a + b
        assert c.format == TextFormat.PLAIN

    def test_textcontent_add_not_textcontent(self):
        a = TextContent("abc")
        with pytest.raises(TypeError):
            a + 1

    def test_textcontent_non_string_raises(self):
        with pytest.raises(TypeError):
            TextContent(123)

    def test_plain_text(self):
        pt = PlainText("plain")
        assert pt.format == TextFormat.PLAIN

    def test_markdown_text(self):
        mt = MarkdownText("# md")
        assert mt.format == TextFormat.MARKDOWN

    def test_html_text(self):
        ht = HtmlText("<b>x</b>")
        assert ht.format == TextFormat.HTML

    def test_title_validation(self):
        t = Title("正しいタイトル")
        assert str(t) == "正しいタイトル"
        with pytest.raises(ValueError):
            Title("")
        with pytest.raises(ValueError):
            Title("  ")
        with pytest.raises(ValueError):
            Title("あ" * 201)

    def test_summary_none_to_empty(self):
        s = Summary(None)
        assert s.value == ""

    def test_catchcopy(self):
        c = Catchcopy("キャッチコピー")
        assert str(c) == "キャッチコピー"
        with pytest.raises(ValueError):
            Catchcopy("あ" * 256)

    def test_genre(self):
        g = Genre(None)
        assert g.value == ""


class TestScoreVO:
    """Score value objects のテスト."""

    def test_quality_score_valid(self):
        q = QualityScore(value=80, dimension="story")
        assert q.is_passing() is True
        assert q.is_passing(threshold=90) is False
        assert str(q) == "story: 80/100"

    def test_quality_score_invalid_type(self):
        with pytest.raises(TypeError):
            QualityScore(value=80.5, dimension="story")

    def test_quality_score_invalid_range(self):
        with pytest.raises(ValueError):
            QualityScore(value=101, dimension="story")

    def test_quality_score_invalid_dimension(self):
        with pytest.raises(ValueError):
            QualityScore(value=50, dimension="unknown_dim")

    def test_tension_score(self):
        t = TensionScore(value=85, delta=25)
        assert t.is_catharsis() is True
        assert t.is_rising() is True
        assert t.is_falling() is False

    def test_tension_score_invalid(self):
        with pytest.raises(ValueError):
            TensionScore(value=101)

    def test_tension_score_falling(self):
        t = TensionScore(value=30, delta=-10)
        assert t.is_falling() is True

    def test_book_score_calculation(self):
        dims = {"story": 80, "character": 60, "prose": 100}
        score = BookScore.calculate_from_dimensions(dims)
        # calculate_from_dimensions はクラス変数 WEIGHTS を使用
        assert score.overall in range(0, 101)
        assert score.get_dimension("story") == 80
        assert score.dimensions == dims

    def test_book_score_empty_dimensions(self):
        score = BookScore.calculate_from_dimensions({})
        assert score.overall == 0

    def test_book_score_invalid_overall(self):
        with pytest.raises(ValueError):
            BookScore(overall=101)

    def test_book_score_invalid_dim(self):
        with pytest.raises(ValueError):
            BookScore(overall=50, dimensions={"story": 101})

    def test_book_score_get_quality_score(self):
        score = BookScore(overall=70, dimensions={"story": 70})
        qs = score.get_quality_score("story")
        assert qs is not None
        assert qs.value == 70
        assert score.get_quality_score("nonexistent") is None

    def test_book_score_str(self):
        score = BookScore(overall=70, dimensions={"story": 70})
        assert "overall=70" in str(score)

    def test_qol_score(self):
        q = QolScore(value=50, factors={"pacing": 70})
        assert q.value == 50
        with pytest.raises(ValueError):
            QolScore(value=101)

    def test_cost_score(self):
        c = CostScore(value=1.5, tokens_used=10000)
        assert c.value == 1.5
        with pytest.raises(ValueError):
            CostScore(value=-0.1)


class TestMetadataVO:
    """Metadata value objects のテスト."""

    def _make_metadata(self) -> NovelMetadata:
        return NovelMetadata(
            novel_id=NovelId.generate(),
            title=Title("作品名"),
            author_id=UserId.generate(),
            genre=Genre("fantasy"),
            catchcopy=Catchcopy("キャッチ"),
            synopsis=Summary("あらすじ"),
            concept=Summary("コンセプト"),
        )

    def test_novel_metadata_defaults(self):
        m = self._make_metadata()
        assert m.status == NovelStatus.DRAFT
        assert m.mode == NovelMode.EASY
        assert m.target_episodes == 50
        assert m.sanctuary_integrity == 100

    def test_novel_metadata_invalid_episodes(self):
        with pytest.raises(ValueError):
            NovelMetadata(
                novel_id=NovelId.generate(),
                title=Title("t"),
                author_id=UserId.generate(),
                genre=Genre(""),
                catchcopy=Catchcopy(""),
                synopsis=Summary(""),
                concept=Summary(""),
                target_episodes=0,
            )

    def test_with_updated_timestamp(self):
        m1 = self._make_metadata()
        m2 = m1.with_updated_timestamp()
        assert m2.novel_id == m1.novel_id
        assert m2.updated_at >= m1.updated_at

    def test_publish_metadata(self):
        pm = PublishMetadata(novel_id=NovelId.generate(), platform=PublishPlatform.NAROU)
        assert pm.status == PublishStatus.PENDING
        assert pm.episode_range_start == 1

    def test_publish_metadata_invalid_range(self):
        with pytest.raises(ValueError):
            PublishMetadata(novel_id=NovelId.generate(), platform=PublishPlatform.KINDLE, episode_range_start=0)

    def test_publish_metadata_range_end_before_start(self):
        with pytest.raises(ValueError):
            PublishMetadata(
                novel_id=NovelId.generate(), platform=PublishPlatform.KINDLE,
                episode_range_start=5, episode_range_end=1,
            )

    def test_chapter_metadata(self):
        cm = ChapterMetadata(
            chapter_id=NovelId.generate(), novel_id=NovelId.generate(),
            episode_number=1, title=Title("第1話"),
        )
        assert cm.is_anchor is False

    def test_chapter_metadata_invalid(self):
        with pytest.raises(ValueError):
            ChapterMetadata(
                chapter_id=NovelId.generate(), novel_id=NovelId.generate(),
                episode_number=0, title=Title("x"),
            )

    def test_character_metadata(self):
        cm = CharacterMetadata(
            character_id=NovelId.generate(), novel_id=NovelId.generate(),
            name="勇者", role="protagonist",
        )
        assert cm.name == "勇者"

    def test_character_metadata_invalid_name(self):
        with pytest.raises(ValueError):
            CharacterMetadata(
                character_id=NovelId.generate(), novel_id=NovelId.generate(),
                name="  ", role="x",
            )

    def test_branch_metadata(self):
        bm = BranchMetadata(branch_id=NovelId.generate(), novel_id=NovelId.generate(), name="IFルート")
        assert bm.fork_episode == 0

    def test_branch_metadata_invalid(self):
        with pytest.raises(ValueError):
            BranchMetadata(branch_id=NovelId.generate(), novel_id=NovelId.generate(), name="")

    def test_audit_metadata(self):
        am = AuditMetadata(
            audit_id=NovelId.generate(), novel_id=NovelId.generate(),
            episode_number=3, category="logic", severity="high",
        )
        assert am.severity == "high"

    def test_audit_metadata_invalid(self):
        with pytest.raises(ValueError):
            AuditMetadata(
                audit_id=NovelId.generate(), novel_id=NovelId.generate(),
                episode_number=0, category="x", severity="y",
            )

    def test_setting_type_enum(self):
        assert SettingType.WORLDVIEW.value == "worldview"
        assert SettingType.CUSTOM.value == "custom"
