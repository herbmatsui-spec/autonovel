from src.domain.entities.novel import Novel
from src.domain.value_objects.ids import UserId
from src.domain.value_objects.metadata import NovelStatus

def test_novel_entity_creation():
    author_id = UserId.generate()
    novel = Novel.create(
        title="覇権を掴む最強の転生者",
        author_id=author_id,
        genre="fantasy",
        synopsis="現代から異世界に転生した男の物語"
    )
    assert str(novel.title) == "覇権を掴む最強の転生者"
    assert novel.status == NovelStatus.DRAFT

def test_novel_status_transition():
    author_id = UserId.generate()
    novel = Novel.create(
        title="テスト",
        author_id=author_id
    )
    novel.status = NovelStatus.PUBLISHED
    assert novel.status == NovelStatus.PUBLISHED
