"""BookMapper の単体テスト。"""
from datetime import datetime
from src.backend.database.models import Book
from src.domain.entities.novel import Novel
from src.domain.value_objects.ids import NovelId, UserId
from src.domain.value_objects.text import Title, Genre, Catchcopy, Summary
from src.domain.value_objects.metadata import NovelStatus, NovelMode
from src.infrastructure.database.mappers.book_mapper import BookMapper


def test_book_mapper_to_domain():
    now = datetime.now()
    orm = Book(
        id=123,
        user_id=456,
        title="テスト作品タイトル",
        genre="ファンタジー",
        concept="最強の魔王が現代に転生",
        synopsis="現代に転生した魔王が無双する物語",
        catchcopy="魔王、現代に立つ",
        target_eps=24,
        style_dna="default",
        status="draft",
        cumulative_tension=15.5,
        created_at=now,
    )

    domain = BookMapper.to_domain(orm)

    assert domain.id.value == "123"
    assert domain.author_id.value == "456"
    assert domain.title.value == "テスト作品タイトル"
    assert domain.genre.value == "ファンタジー"
    assert domain.concept.value == "最強の魔王が現代に転生"
    assert domain.synopsis.value == "現代に転生した魔王が無双する物語"
    assert domain.catchcopy.value == "魔王、現代に立つ"
    assert domain.target_episodes == 24
    assert domain.style_dna == "default"
    assert domain.status == NovelStatus.DRAFT
    assert domain.mode == NovelMode.EASY
    assert domain.cumulative_tension == 15


def test_book_mapper_to_orm():
    now = datetime.now()
    domain = Novel(
        id=NovelId("789"),
        author_id=UserId("101"),
        title=Title("ドメインタイトル"),
        genre=Genre("SF"),
        concept=Summary("宇宙船の旅"),
        synopsis=Summary("遥かなる星を目指して"),
        catchcopy=Catchcopy("星の果てへ"),
        target_episodes=12,
        style_dna="hard_sf",
        status=NovelStatus.DRAFT,
        mode=NovelMode.EASY,
        created_at=now,
        updated_at=now,
        cumulative_tension=10,
    )

    orm = BookMapper.to_orm(domain)

    assert orm.id == 789
    assert orm.user_id == 101
    assert orm.title == "ドメインタイトル"
    assert orm.genre == "SF"
    assert orm.concept == "宇宙船の旅"
    assert orm.synopsis == "遥かなる星を目指して"
    assert orm.catchcopy == "星の果てへ"
    assert orm.target_eps == 12
    assert orm.style_key == "hard_sf"
    assert orm.status == "draft"
    assert orm.cumulative_tension == 10.0
