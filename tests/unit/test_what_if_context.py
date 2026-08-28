import pytest
from unittest.mock import AsyncMock, MagicMock
from src.agents.what_if_generator import WhatIfGenerator
from src.agents.afterglow_generator import AfterglowGenerator
from src.schemas.ux_schemas import WhatIfRequest
from src.models.context_bus import BibleContext, CharacterContext


@pytest.mark.asyncio
async def test_what_if_generator_with_bible_context():
    mock_llm_gateway = MagicMock()
    mock_llm_gateway.generate_text = AsyncMock(return_value="主人公は裏ルートを選択し、影から敵を壊滅させた。")

    mock_bible_service = MagicMock()
    mc_ctx = CharacterContext(
        name="レン",
        personality="冷徹で合理的",
        iron_constraint="無辜の民を決して巻き込まない",
        social_mask_vs_truth="表向きは傭兵、裏では反乱軍の参謀",
        first_person="俺",
        second_person="お前",
    )
    mock_bible_context = BibleContext(
        book_id=99,
        title="反逆の刃",
        mc=mc_ctx,
    )
    mock_bible_service.get_context_by_book_id = AsyncMock(return_value=mock_bible_context)

    generator = WhatIfGenerator(
        llm_gateway=mock_llm_gateway,
        bible_service=mock_bible_service,
    )

    req = WhatIfRequest(
        book_id=99,
        choice_point="敵の罠と知りつつ正面から突入するか？",
        novel_context="主人公は敵本拠地の前に立っている。",
    )

    res = await generator.generate_branch(req)
    assert res.choice_point == "敵の罠と知りつつ正面から突入するか？"
    assert "主人公は裏ルートを選択し" in res.alternative_snippet

    mock_llm_gateway.generate_text.assert_called_once()
    call_args = mock_llm_gateway.generate_text.call_args
    assert call_args[0][0] == "what_if" or call_args[1].get("purpose_or_request") == "what_if"
    called_prompt = call_args[1]["prompt"]
    assert "無辜の民を決して巻き込まない" in called_prompt
    assert "レン" in called_prompt


@pytest.mark.asyncio
async def test_afterglow_generator_with_bible_context():
    mock_llm_gateway = MagicMock()
    mock_llm_gateway.generate_text = AsyncMock(return_value="（……あいつ、無茶ばかりして。でも、助けてくれて嬉しかったなんて言えるわけないでしょ……）")

    mock_bible_service = MagicMock()
    sub_ctx = CharacterContext(
        name="フィオナ",
        role="王女",
        tone="〜ですわ、強気な貴族調",
        suffix_style="ですわ",
        first_person="わたくし",
        second_person="貴方",
        social_mask_vs_truth="高飛車な王女を演じるが、実は孤独で泣き虫",
        secrets=["暗殺の標的になっている"],
    )
    mock_bible_context = BibleContext(
        book_id=99,
        title="反逆の刃",
        characters={"フィオナ": sub_ctx},
    )
    mock_bible_service.get_context_by_book_id = AsyncMock(return_value=mock_bible_context)

    afterglow = AfterglowGenerator(
        llm_gateway=mock_llm_gateway,
        bible_service=mock_bible_service,
    )

    res = await afterglow.generate_monologue(
        character_name="フィオナ",
        scene_type="救援直後",
        context="主人公が身を挺してフィオナを救出した。",
        book_id=99,
    )

    assert res.character_name == "フィオナ"
    mock_llm_gateway.generate_text.assert_called_once()
    call_args = mock_llm_gateway.generate_text.call_args
    assert call_args[0][0] == "afterglow" or call_args[1].get("purpose_or_request") == "afterglow"
    called_prompt = call_args[1]["prompt"]
    assert "フィオナ" in called_prompt
    assert "高飛車な王女を演じるが、実は孤独で泣き虫" in called_prompt
    assert "暗殺の標的になっている" in called_prompt
