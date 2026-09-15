"""CharacterDomainService（キャラクタードメインサービス）の単体テスト."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.domain.domain_services.character_domain_service import (
    CharacterDomainService, CharacterValidator, CharacterConsistencyChecker,
    CharacterRelationshipManager, CharacterValidationError,
    RelationshipType, CharacterRelationship, CharacterConsistencyIssue,
)
from src.domain.entities.character import Character, CharacterArc
from src.domain.value_objects.ids import NovelId, CharacterId


def make_mock_repo() -> MagicMock:
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=None)
    repo.get_by_name = AsyncMock(return_value=None)
    repo.save = AsyncMock(side_effect=lambda c: c)
    repo.save_arc = AsyncMock(side_effect=lambda a: a)
    repo.list_by_novel = AsyncMock(return_value=[])
    repo.delete = AsyncMock(return_value=True)
    repo.get_arc = AsyncMock(return_value=None)
    return repo


def make_service() -> CharacterDomainService:
    return CharacterDomainService(character_repo=make_mock_repo())


class TestCharacterValidator:
    """CharacterValidator のテスト."""

    def test_validate_character_ok(self):
        c = Character.create(novel_id=NovelId.generate(), name="勇者", role="protagonist")
        assert CharacterValidator.validate_character(c) == []

    def test_validate_character_empty_name(self):
        c = Character.create(novel_id=NovelId.generate(), name="x", role="y")
        c.name = "  "
        errors = CharacterValidator.validate_character(c)
        assert any("name" in e for e in errors)

    def test_validate_character_empty_role(self):
        c = Character.create(novel_id=NovelId.generate(), name="x", role="y")
        c.role = ""
        errors = CharacterValidator.validate_character(c)
        assert any("role" in e for e in errors)

    def test_validate_character_arc_ok(self):
        novel_id = NovelId.generate()
        char_id = CharacterId.generate()
        arc = CharacterArc.create(novel_id=novel_id, character_id=char_id, arc_name="成長", stages=["a", "b"])
        assert CharacterValidator.validate_character_arc(arc) == []

    def test_validate_character_arc_empty_name(self):
        novel_id = NovelId.generate()
        char_id = CharacterId.generate()
        arc = CharacterArc.create(novel_id=novel_id, character_id=char_id, arc_name="x", stages=["a"])
        arc.arc_name = ""
        errors = CharacterValidator.validate_character_arc(arc)
        assert len(errors) == 1

    def test_validate_character_arc_no_stages(self):
        novel_id = NovelId.generate()
        char_id = CharacterId.generate()
        arc = CharacterArc.create(novel_id=novel_id, character_id=char_id, arc_name="x", stages=[])
        errors = CharacterValidator.validate_character_arc(arc)
        assert any("stage" in e for e in errors)

    def test_validate_character_arc_index_out_of_bounds(self):
        novel_id = NovelId.generate()
        char_id = CharacterId.generate()
        arc = CharacterArc.create(novel_id=novel_id, character_id=char_id, arc_name="x", stages=["a", "b"])
        arc.current_stage_index = 5
        errors = CharacterValidator.validate_character_arc(arc)
        assert any("bounds" in e for e in errors)


class TestCharacterConsistencyChecker:
    """CharacterConsistencyChecker のテスト."""

    @pytest.mark.asyncio
    async def test_check_not_found(self):
        repo = make_mock_repo()
        checker = CharacterConsistencyChecker(repo)
        issues = await checker.check_character_consistency(NovelId.generate(), CharacterId.generate())
        assert len(issues) == 1
        assert issues[0].issue_type == "not_found"

    @pytest.mark.asyncio
    async def test_check_duplicate_role(self):
        novel_id = NovelId.generate()
        char = Character.create(novel_id=novel_id, name="A", role="hero")
        other = Character.create(novel_id=novel_id, name="B", role="hero")
        repo = make_mock_repo()
        repo.get_by_id = AsyncMock(return_value=char)
        repo.list_by_novel = AsyncMock(return_value=[char, other])
        checker = CharacterConsistencyChecker(repo)
        issues = await checker.check_character_consistency(novel_id, char.id)
        assert any(i.issue_type == "duplicate_role" for i in issues)

    @pytest.mark.asyncio
    async def test_check_arc_mismatch(self):
        # add_arc は novel_id 不一致を ValueError で防ぐが、
        # checker._check_arc_consistency は直接呼び出すことで検証できる
        novel_id = NovelId.generate()
        char = Character.create(novel_id=novel_id, name="A", role="hero")
        wrong_novel = NovelId.generate()
        arc = CharacterArc.create(novel_id=wrong_novel, character_id=char.id, arc_name="x", stages=["a"])
        repo = make_mock_repo()
        checker = CharacterConsistencyChecker(repo)
        issues = checker._check_arc_consistency(char, arc)
        assert any(i.issue_type == "arc_mismatch" and "novel_id" in i.field for i in issues)


class TestCharacterRelationshipManager:
    """CharacterRelationshipManager のテスト."""

    def setup_method(self):
        self.manager = CharacterRelationshipManager()

    def test_add_relationship_mutual(self):
        c1, c2 = CharacterId.generate(), CharacterId.generate()
        rel = self.manager.add_relationship(c1, c2, RelationshipType.MENTOR, strength=70)
        assert rel.relationship_type == RelationshipType.MENTOR
        # 逆向きの関係（MENTOR→SUBORDINATE）が自動登録される
        reverse = self.manager.get_relationship(c2, c1)
        assert reverse is not None
        assert reverse.relationship_type == RelationshipType.SUBORDINATE

    def test_add_relationship_invalid_strength(self):
        with pytest.raises(ValueError):
            self.manager.add_relationship(CharacterId.generate(), CharacterId.generate(), RelationshipType.ALLY, strength=150)

    def test_get_relationships(self):
        c1, c2 = CharacterId.generate(), CharacterId.generate()
        self.manager.add_relationship(c1, c2, RelationshipType.ALLY)
        rels = self.manager.get_relationships(c1)
        assert len(rels) == 1

    def test_update_relationship_strength(self):
        c1, c2 = CharacterId.generate(), CharacterId.generate()
        self.manager.add_relationship(c1, c2, RelationshipType.ALLY, strength=50)
        assert self.manager.update_relationship_strength(c1, c2, 80) is True
        rel = self.manager.get_relationship(c1, c2)
        assert rel.strength == 80
        # 存在しない組み合わせ
        assert self.manager.update_relationship_strength(CharacterId.generate(), c2, 10) is False
        # 範囲外
        with pytest.raises(ValueError):
            self.manager.update_relationship_strength(c1, c2, 200)

    def test_remove_relationship_mutual(self):
        c1, c2 = CharacterId.generate(), CharacterId.generate()
        self.manager.add_relationship(c1, c2, RelationshipType.ALLY)
        assert self.manager.remove_relationship(c1, c2) is True
        assert self.manager.get_relationship(c1, c2) is None
        assert self.manager.get_relationship(c2, c1) is None  # 逆向きも削除
        assert self.manager.remove_relationship(c1, c2) is False

    def test_get_reverse_type(self):
        assert self.manager._get_reverse_type(RelationshipType.MENTOR) == RelationshipType.SUBORDINATE
        assert self.manager._get_reverse_type(RelationshipType.ALLY) == RelationshipType.ALLY


class TestCharacterDomainService:
    """CharacterDomainService ファサードのテスト."""

    @pytest.mark.asyncio
    async def test_create_character_ok(self):
        service = make_service()
        c = await service.create_character(NovelId.generate(), "勇者", "protagonist")
        assert c.name == "勇者"
        service.character_repo.save.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_character_validation_error(self):
        service = make_service()
        c = Character.create(novel_id=NovelId.generate(), name="x", role="y")
        c.name = "  "  # 不正な名前に変更
        service.character_repo.save = AsyncMock(return_value=c)
        # create_character は内部で Character.create を呼ぶため直接エラーは起きにくい。
        # validate のエラー経路を通すため validator をモック
        service._validator.validate_character = lambda x: ["Character name cannot be empty"]
        with pytest.raises(CharacterValidationError):
            await service.create_character(NovelId.generate(), "", "y")

    @pytest.mark.asyncio
    async def test_get_character(self):
        service = make_service()
        existing = Character.create(novel_id=NovelId.generate(), name="A", role="x")
        service.character_repo.get_by_id = AsyncMock(return_value=existing)
        got = await service.get_character(existing.id)
        assert got is existing

    @pytest.mark.asyncio
    async def test_get_character_by_name(self):
        service = make_service()
        existing = Character.create(novel_id=NovelId.generate(), name="A", role="x")
        service.character_repo.get_by_name = AsyncMock(return_value=existing)
        got = await service.get_character_by_name(NovelId.generate(), "A")
        assert got is existing

    @pytest.mark.asyncio
    async def test_update_character_not_found(self):
        service = make_service()
        with pytest.raises(CharacterValidationError):
            await service.update_character(CharacterId.generate(), name="new")

    @pytest.mark.asyncio
    async def test_update_character_ok(self):
        service = make_service()
        existing = Character.create(novel_id=NovelId.generate(), name="A", role="x")
        service.character_repo.get_by_id = AsyncMock(return_value=existing)
        result = await service.update_character(existing.id, name="B", personality="勇敢")
        assert result.name == "B"
        assert result.personality == "勇敢"

    @pytest.mark.asyncio
    async def test_list_characters(self):
        service = make_service()
        c1 = Character.create(novel_id=NovelId.generate(), name="A", role="x")
        service.character_repo.list_by_novel = AsyncMock(return_value=[c1])
        chars = await service.list_characters(NovelId.generate())
        assert chars == [c1]

    @pytest.mark.asyncio
    async def test_delete_character(self):
        service = make_service()
        assert await service.delete_character(CharacterId.generate()) is True

    @pytest.mark.asyncio
    async def test_create_character_arc_not_found(self):
        service = make_service()
        with pytest.raises(CharacterValidationError):
            await service.create_character_arc(NovelId.generate(), CharacterId.generate(), "arc", ["a"])

    @pytest.mark.asyncio
    async def test_create_character_arc_ok(self):
        service = make_service()
        novel_id = NovelId.generate()
        char = Character.create(novel_id=novel_id, name="A", role="x")
        service.character_repo.get_by_id = AsyncMock(return_value=char)
        arc = await service.create_character_arc(novel_id, char.id, "成長", ["a", "b"])
        assert arc.arc_name == "成長"
        service.character_repo.save_arc.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_advance_character_arc_not_found(self):
        service = make_service()
        with pytest.raises(CharacterValidationError):
            await service.advance_character_arc(CharacterId.generate())

    @pytest.mark.asyncio
    async def test_advance_character_arc_ok(self):
        service = make_service()
        novel_id = NovelId.generate()
        char_id = CharacterId.generate()
        arc = CharacterArc.create(novel_id=novel_id, character_id=char_id, arc_name="x", stages=["a", "b"])
        service.character_repo.get_arc = AsyncMock(return_value=arc)
        result = await service.advance_character_arc(arc.id)
        assert result.current_stage_index == 1

    @pytest.mark.asyncio
    async def test_get_character_arcs_not_found(self):
        service = make_service()
        result = await service.get_character_arcs(CharacterId.generate())
        assert result == []

    @pytest.mark.asyncio
    async def test_get_current_arc(self):
        service = make_service()
        novel_id = NovelId.generate()
        char = Character.create(novel_id=novel_id, name="A", role="x")
        arc = CharacterArc.create(novel_id=novel_id, character_id=char.id, arc_name="x", stages=["a"])
        char.add_arc(arc)
        service.character_repo.get_by_id = AsyncMock(return_value=char)
        current = await service.get_current_arc(char.id)
        assert current is arc

    @pytest.mark.asyncio
    async def test_check_consistency_delegates(self):
        service = make_service()
        issues = await service.check_consistency(NovelId.generate(), CharacterId.generate())
        assert len(issues) == 1  # not_found

    @pytest.mark.asyncio
    async def test_check_all_consistency(self):
        service = make_service()
        c1 = Character.create(novel_id=NovelId.generate(), name="A", role="x")
        service.character_repo.list_by_novel = AsyncMock(return_value=[c1])
        result = await service.check_all_consistency(NovelId.generate())
        # not_found の issue が1件
        assert len(result) == 1

    def test_add_and_get_relationship(self):
        service = make_service()
        c1, c2 = CharacterId.generate(), CharacterId.generate()
        rel = service.add_relationship(c1, c2, RelationshipType.RIVAL, strength=60)
        assert rel.relationship_type == RelationshipType.RIVAL
        rels = service.get_relationships(c1)
        assert len(rels) == 1
        got = service.get_relationship(c1, c2)
        assert got is rel
        assert service.update_relationship_strength(c1, c2, 90) is True
        assert service.remove_relationship(c1, c2) is True

    @pytest.mark.asyncio
    async def test_get_character_with_relationships(self):
        service = make_service()
        char = Character.create(novel_id=NovelId.generate(), name="A", role="x")
        service.character_repo.get_by_id = AsyncMock(return_value=char)
        got = await service.get_character_with_relationships(char.id)
        assert got is char

    @pytest.mark.asyncio
    async def test_get_character_metadata(self):
        service = make_service()
        char = Character.create(novel_id=NovelId.generate(), name="A", role="x")
        service.character_repo.get_by_id = AsyncMock(return_value=char)
        metadata = await service.get_character_metadata(char.id)
        assert metadata is not None
        assert metadata.name == "A"

    @pytest.mark.asyncio
    async def test_validate_new_character_duplicate_name(self):
        service = make_service()
        novel_id = NovelId.generate()
        existing = Character.create(novel_id=novel_id, name="A", role="protagonist")
        service.character_repo.get_by_name = AsyncMock(return_value=existing)
        service.character_repo.list_by_novel = AsyncMock(return_value=[existing])
        warnings = await service.validate_new_character(novel_id, "A", "protagonist")
        assert any("already exists" in w for w in warnings)
        # 既存の主人公ロールに対する警告も検出される
        assert any("main character" in w for w in warnings)

    @pytest.mark.asyncio
    async def test_validate_new_character_ok(self):
        service = make_service()
        service.character_repo.get_by_name = AsyncMock(return_value=None)
        service.character_repo.list_by_novel = AsyncMock(return_value=[])
        warnings = await service.validate_new_character(NovelId.generate(), "NewChar", "support")
        assert warnings == []
