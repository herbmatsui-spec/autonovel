import pytest
from unittest.mock import AsyncMock, MagicMock
from src.agents.illustration_agent import IllustrationAgent
from src.models.illustration import IllustrationRequest, IllustrationType
from src.models.context_bus import BibleContext, CharacterContext
from src.services.illustration.character_service import CharacterIllustrator


@pytest.mark.asyncio
async def test_character_illustrator_auto_enrichment_from_bible():
    # Mock ImageService
    mock_image_service = MagicMock()
    mock_image_service.generate = AsyncMock(return_value="http://example.com/alice.png")

    # Mock BibleService
    mock_bible_service = MagicMock()
    alice_ctx = CharacterContext(
        name="アリス",
        role="大魔導士",
        appearance="銀髪ロングヘア、サファイア色の瞳、白銀のローブ",
        visual_tags=["silver hair", "blue eyes", "white robe"],
        personality="おしとやか",
    )
    mock_bible_context = BibleContext(
        book_id=10,
        title="テスト作品",
        characters={"アリス": alice_ctx},
    )
    mock_bible_service.get_context_by_book_id = AsyncMock(return_value=mock_bible_context)

    # Instantiate CharacterIllustrator with bible_service
    illustrator = CharacterIllustrator(
        image_service=mock_image_service,
        bible_service=mock_bible_service,
    )

    req = IllustrationRequest(
        book_id=10,
        illustration_type=IllustrationType.CHARACTER,
        character_id="アリス",
        book_context={"name": "アリス"},  # appearance is empty, should be auto-enriched
    )

    res = await illustrator.generate(req)
    assert res.image_url == "http://example.com/alice.png"
    assert "アリス" in res.prompt
    assert "銀髪ロングヘア" in res.prompt or "silver hair" in res.prompt

    # Verify generate was called with enriched prompt
    mock_image_service.generate.assert_called_once()
    call_prompt = mock_image_service.generate.call_args[1]["prompt"]
    assert "大魔導士" in call_prompt
    assert "銀髪ロングヘア" in call_prompt


@pytest.mark.asyncio
async def test_illustration_agent_with_bible_service():
    mock_image_service = MagicMock()
    mock_image_service.generate = AsyncMock(return_value="http://example.com/mc.png")

    mock_bible_service = MagicMock()
    mc_ctx = CharacterContext(
        name="レオ",
        role="勇者",
        appearance="金髪碧眼、赤のマント",
        visual_tags=["blonde", "blue eyes", "red cape"],
    )
    mock_bible_context = BibleContext(
        book_id=1,
        title="勇者譚",
        mc=mc_ctx,
    )
    mock_bible_service.get_context_by_book_id = AsyncMock(return_value=mock_bible_context)

    agent = IllustrationAgent(
        image_service=mock_image_service,
        bible_service=mock_bible_service,
    )

    req = IllustrationRequest(
        book_id=1,
        illustration_type=IllustrationType.CHARACTER,
        character_id="mc",
    )

    out = await agent.run(request=req)
    assert out["status"] == "success"
    assert out["result"].image_url == "http://example.com/mc.png"
    assert "レオ" in out["result"].prompt
