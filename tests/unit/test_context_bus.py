import pytest
from src.models import CharacterRegistry, WorldBible, WorldRules
from src.services.bible_service import BibleService, BibleContextBus


def test_extract_character_context():
    bus = BibleService()
    char = CharacterRegistry(
        name="アリス",
        role="魔術師",
        gender="女性",
        age="17",
        appearance="銀髪ロング、碧眼、白いローブ",
        personality="冷静沈着、実は甘党",
        surface_persona="冷徹な宮廷魔術師",
        inner_conflict="本当は自由に旅をしたい",
        iron_constraint="味方を決して見捨てない",
        tone="丁寧語、〜ですわ",
        first_person="私",
        second_person="あなた",
        suffix_style="ですわ",
        social_mask_vs_truth="表向きは冷徹だが夜に一人でお菓子を焼く",
        known_facts=["古代帝国の真実"],
        unknown_facts=["国王の裏切り計画"],
    )

    ctx = bus.extract_character_context(char)
    assert ctx.name == "アリス"
    assert ctx.role == "魔術師"
    assert "銀髪ロング" in ctx.appearance
    assert "銀髪ロング" in ctx.visual_tags
    assert ctx.first_person == "私"
    assert ctx.social_mask_vs_truth == "表向きは冷徹だが夜に一人でお菓子を焼く"
    assert ctx.secrets == ["表向きは冷徹だが夜に一人でお菓子を焼く"]

    prompt = ctx.to_appearance_prompt()
    assert "女性" in prompt
    assert "銀髪ロング" in prompt


def test_export_full_context():
    bus = BibleContextBus()
    mc = CharacterRegistry(
        name="カイト",
        role="主人公",
        appearance="黒髪短髪、精悍な顔つき、黒の剣士装束",
        personality="不屈の闘志",
    )
    sub = CharacterRegistry(
        name="ルナ",
        role="ヒロイン",
        appearance="金髪ツインテール、紅蓮の瞳、魔法少女ドレス",
        personality="ツンデレ",
    )
    bible = WorldBible(
        title="剣と魔法の物語",
        genre="ファンタジー",
        concept="異世界無双",
        mc_profile=mc,
        sub_characters=[sub],
        world_settings=WorldRules(rules=["魔法は魔力を消費する", "魔王は封印されている"]),
    )

    full_ctx = bus.export_full_context(bible, book_id=42)
    assert full_ctx.book_id == 42
    assert full_ctx.title == "剣と魔法の物語"
    assert full_ctx.mc is not None
    assert full_ctx.mc.name == "カイト"
    assert "ルナ" in full_ctx.characters

    # Helper functions
    char_k = full_ctx.get_character("カイト")
    assert char_k is not None
    assert char_k.name == "カイト"

    char_hero = full_ctx.get_character("mc")
    assert char_hero is not None
    assert char_hero.name == "カイト"

    vis_luna = full_ctx.get_character_appearance_prompt("ルナ")
    assert "金髪ツインテール" in vis_luna
