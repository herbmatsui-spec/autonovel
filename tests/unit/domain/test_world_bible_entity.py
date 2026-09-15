"""WorldBible/PendingSetting/Setting/Lore entities の単体テスト."""

import pytest
from datetime import datetime

from src.domain.entities.world_bible import WorldBible, PendingSetting, Setting, Lore
from src.domain.value_objects.ids import NovelId, SettingId
from src.domain.value_objects.text import TextContent, MarkdownText


class TestWorldBible:
    """WorldBible aggregate root のテスト."""

    def test_create_factory(self):
        bible = WorldBible.create(NovelId.generate())
        assert isinstance(bible.id, SettingId)
        assert bible.version == 1
        assert bible.settings.content == ""
        assert bible.revealed.content == ""

    def test_update_settings_version_increment(self):
        bible = WorldBible.create(NovelId.generate())
        bible.update_settings(MarkdownText("設定内容"), increment_version=True)
        assert bible.version == 2
        assert bible.settings.content == "設定内容"

    def test_update_settings_no_increment(self):
        bible = WorldBible.create(NovelId.generate())
        bible.update_settings(MarkdownText("x"), increment_version=False)
        assert bible.version == 1

    def test_update_revealed(self):
        bible = WorldBible.create(NovelId.generate())
        bible.update_revealed(MarkdownText("読者既知情報"))
        assert bible.revealed.content == "読者既知情報"

    def test_pending_settings_lifecycle(self):
        bible = WorldBible.create(NovelId.generate())
        pending = bible.add_pending_setting("magic", TextContent("魔法追加"), confidence=0.8)
        assert pending.status == "pending"
        assert bible.get_pending_settings() == [pending]
        assert bible.get_pending_setting("magic") == pending

        confirmed = bible.confirm_pending_setting("magic")
        assert confirmed is not None
        assert confirmed.status == "pending"  # statusはそのまま、bibleからは削除
        assert bible.get_pending_setting("magic") is None

    def test_pending_settings_reject(self):
        bible = WorldBible.create(NovelId.generate())
        bible.add_pending_setting("tech", TextContent("技術追加"), confidence=0.5)
        rejected = bible.reject_pending_setting("tech")
        assert rejected is not None
        assert bible.get_pending_setting("tech") is None

    def test_add_pending_setting_invalid_confidence(self):
        bible = WorldBible.create(NovelId.generate())
        with pytest.raises(ValueError):
            bible.add_pending_setting("x", TextContent("y"), confidence=1.5)

    def test_add_pending_setting_empty_field(self):
        bible = WorldBible.create(NovelId.generate())
        with pytest.raises(ValueError):
            bible.add_pending_setting("  ", TextContent("y"))

    def test_to_dict_from_dict_roundtrip(self):
        bible = WorldBible.create(NovelId.generate())
        bible.update_settings(MarkdownText("設定"), increment_version=False)
        bible.update_revealed(MarkdownText("既知"))
        d = bible.to_dict()
        restored = WorldBible.from_dict(d)
        assert restored.id == bible.id
        assert restored.novel_id == bible.novel_id
        assert restored.settings.content == "設定"
        assert restored.revealed.content == "既知"
        assert restored.version == bible.version

    def test_eq_hash(self):
        novel_id = NovelId.generate()
        b1 = WorldBible.create(novel_id)
        b2 = WorldBible.create(novel_id)
        assert b1 != b2
        assert b1 != "not a bible"

    def test_hash_same_id(self):
        novel_id = NovelId.generate()
        b1 = WorldBible.create(novel_id)
        clone = WorldBible(
            id=b1.id, novel_id=b1.novel_id, settings=b1.settings, revealed=b1.revealed,
        )
        assert hash(b1) == hash(clone)


class TestPendingSetting:
    """PendingSetting value object のテスト."""

    def test_valid(self):
        ps = PendingSetting(
            id=SettingId.generate(), novel_id=NovelId.generate(),
            field_name="magic", proposed_value=TextContent("魔法"), confidence=0.9,
        )
        assert ps.status == "pending"

    def test_invalid_confidence(self):
        with pytest.raises(ValueError):
            PendingSetting(
                id=SettingId.generate(), novel_id=NovelId.generate(),
                field_name="x", proposed_value=TextContent("y"), confidence=2.0,
            )

    def test_invalid_field_name(self):
        with pytest.raises(ValueError):
            PendingSetting(
                id=SettingId.generate(), novel_id=NovelId.generate(),
                field_name="", proposed_value=TextContent("y"), confidence=0.5,
            )


class TestSetting:
    """Setting value object のテスト."""

    def test_valid(self):
        s = Setting(
            id=SettingId.generate(), name="マナ", value=TextContent("魔力"),
            category="magic_system",
        )
        assert s.is_revealed is False

    def test_invalid_name(self):
        with pytest.raises(ValueError):
            Setting(id=SettingId.generate(), name="", value=TextContent("x"), category="y")

    def test_invalid_category(self):
        with pytest.raises(ValueError):
            Setting(id=SettingId.generate(), name="x", value=TextContent("y"), category="")

    def test_mark_revealed_immutable(self):
        s = Setting(id=SettingId.generate(), name="x", value=TextContent("y"), category="z")
        s2 = s.mark_revealed()
        assert s2.is_revealed is True
        assert s.is_revealed is False

    def test_update_value_immutable(self):
        s = Setting(id=SettingId.generate(), name="x", value=TextContent("y"), category="z")
        s2 = s.update_value(TextContent("new"))
        assert s2.value.content == "new"
        assert s.value.content == "y"


class TestLore:
    """Lore value object のテスト."""

    def test_create_factory(self):
        lore = Lore.create(
            novel_id=NovelId.generate(), title="古王国の歴史",
            content=MarkdownText("説明文"), category="history",
        )
        assert lore.is_secret is False
        assert lore.tags == []

    def test_invalid_title(self):
        with pytest.raises(ValueError):
            Lore.create(novel_id=NovelId.generate(), title="", content=MarkdownText("x"), category="y")

    def test_invalid_category(self):
        with pytest.raises(ValueError):
            Lore.create(novel_id=NovelId.generate(), title="x", content=MarkdownText("y"), category="")

    def test_add_tag_dedup(self):
        lore = Lore.create(novel_id=NovelId.generate(), title="x", content=MarkdownText("y"), category="z")
        lore2 = lore.add_tag("古代")
        lore3 = lore2.add_tag("古代")  # 重複
        assert lore2.tags == ["古代"]
        assert lore3.tags == ["古代"]
        assert lore.tags == []  # 元は不変

    def test_add_tag_multiple(self):
        lore = Lore.create(novel_id=NovelId.generate(), title="x", content=MarkdownText("y"), category="z")
        lore2 = lore.add_tag("古代")
        lore3 = lore2.add_tag("魔法")
        assert lore3.tags == ["古代", "魔法"]
