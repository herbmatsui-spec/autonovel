from unittest import mock

import pytest

from src.agents.illustration_agent import IllustrationAgent
from src.models.illustration import (
    IllustrationModel,
    IllustrationRequest,
    IllustrationType,
    SafetyLevel,
)
from src.services.illustration import (
    CharacterIllustrator,
    CoverGenerator,
    SceneExtractor,
    SceneIllustrationService,
    SceneIllustrator,
)
from src.services.illustration.model_selector import resolve_model_id
from src.services.illustration.prompts import (
    apply_safety_modifier,
    build_character_prompt,
    build_cover_prompt,
    build_scene_prompt,
)

# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------


def test_build_cover_prompt_includes_title_and_genre():
    prompt = build_cover_prompt(
        {"title": "天空の城", "genre": "ファンタジー", "concept": "空の城", "keywords": "竜,魔法"}
    )
    assert "天空の城" in prompt
    # ジャンルは視覚スタイルヒント(英語)に変換される
    assert "fantasy" in prompt.lower()
    assert "竜" in prompt
    assert "no text" in prompt.lower()


def test_build_scene_prompt_truncates_long_text():
    long = "海を見た。" * 200
    prompt = build_scene_prompt(long, {"genre": "SF"})
    assert len(prompt) < 2000
    assert "sci-fi" in prompt.lower()


def test_build_character_prompt_includes_appearance():
    prompt = build_character_prompt(
        {"name": "アヤ", "role": "ヒロイン", "appearance": "青い髪", "traits": "勇敢"}
    )
    assert "アヤ" in prompt
    assert "青い髪" in prompt
    assert "勇敢" in prompt


def test_apply_safety_modifier_r15_adds_keywords():
    base = "A scene."
    out = apply_safety_modifier(base, SafetyLevel.R15_CONTENT, IllustrationType.EPISODE)
    assert "r15" in out.lower()
    assert "artistic" in out.lower()
    assert "intimate" in out.lower()


def test_apply_safety_modifier_standard_unchanged():
    base = "A scene."
    out = apply_safety_modifier(base, SafetyLevel.BLOCK_SOME, IllustrationType.EPISODE)
    assert out == base


# ---------------------------------------------------------------------------
# Scene extractor (heuristic, no LLM)
# ---------------------------------------------------------------------------


def test_scene_extractor_picks_visual_paragraphs():
    text = (
        "彼は深く考え込むことにした。\n\n"
        "朝日に照らされた巨大な城が、ゆっくりと空高く浮かんでいた。\n\n"
        "それは単なる推測に過ぎないことだった。\n\n"
        "血に染まった剣を手に、彼女は静かに海の彼方を見つめた。"
    )
    scenes = SceneExtractor().extract_scenes(text, max_scenes=2)
    assert len(scenes) == 2
    joined = " ".join(scenes)
    assert "城" in joined
    assert "剣" in joined


@pytest.mark.asyncio
async def test_scene_extractor_llm_fallback_on_failure():
    text = (
        "彼は深く考え込むことにした。\n\n"
        "朝日に照らされた巨大な城が、ゆっくりと空高く浮かんでいた。\n\n"
        "それは単なる推測に過ぎないことだった。\n\n"
        "血に染まった剣を手に、彼女は静かに海の彼方を見つめた。"
    )
    extractor = SceneExtractor()
    failing_llm = mock.AsyncMock()
    failing_llm.generate_json.side_effect = RuntimeError("LLM unavailable")
    scenes = await extractor.extract_scenes_with_llm(text, failing_llm, max_scenes=2)
    assert len(scenes) == 2
    joined = " ".join(scenes)
    assert "城" in joined
    assert "剣" in joined


# ---------------------------------------------------------------------------
# Services with a fake image service
# ---------------------------------------------------------------------------


def _fake_image_service():
    svc = mock.AsyncMock()
    svc.generate.return_value = "/static/illustrations/fake.png"
    return svc


@pytest.mark.asyncio
async def test_cover_generator_returns_result():
    svc = _fake_image_service()
    agent = CoverGenerator(svc)
    req = IllustrationRequest(
        book_id=1,
        illustration_type=IllustrationType.COVER,
        book_context={"title": "T", "genre": "ファンタジー"},
    )
    result = await agent.generate(req)
    assert result.image_url == "/static/illustrations/fake.png"
    assert "T" in result.prompt
    svc.generate.assert_awaited_once()


@pytest.mark.asyncio
async def test_character_illustrator_builds_prompt():
    svc = _fake_image_service()
    agent = CharacterIllustrator(svc)
    req = IllustrationRequest(
        book_id=1,
        illustration_type=IllustrationType.CHARACTER,
        book_context={"name": "アヤ", "appearance": "銀髪"},
        model=IllustrationModel.FAST,
    )
    result = await agent.generate(req)
    assert "アヤ" in result.prompt
    assert result.model_used == "imagen-4.0-fast-generate-001"


@pytest.mark.asyncio
async def test_scene_illustrator_single_scene():
    svc = _fake_image_service()
    agent = SceneIllustrator(svc)
    req = IllustrationRequest(
        book_id=1,
        illustration_type=IllustrationType.EPISODE,
        book_context={"genre": "SF"},
    )
    result = await agent.generate_for_scene("宇宙船が舞い降りた。", req)
    assert "宇宙船" in result.prompt


@pytest.mark.asyncio
async def test_scene_service_extracts_and_generates():
    svc = _fake_image_service()
    service = SceneIllustrationService(svc, llm=None)
    req = IllustrationRequest(
        book_id=1,
        illustration_type=IllustrationType.EPISODE,
        scene_text=(
            "光る剣を激しく振るい、敵を一掃した。\n\n"
            "ただ座ってじっと考え込んでいた。\n\n"
            "炎の中から巨大な城がゆっくりと現れた。"
        ),
    )
    results = await service.generate(req)
    assert len(results) >= 1
    assert all(r.image_url for r in results)


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_agent_cover_with_fake_service():
    svc = _fake_image_service()
    agent = IllustrationAgent(image_service=svc)
    req = IllustrationRequest(
        book_id=1,
        illustration_type=IllustrationType.COVER,
        book_context={"title": "星の海", "genre": "ファンタジー"},
    )
    res = await agent.run(request=req)
    assert res["status"] == "success"
    assert res["result"].image_url == "/static/illustrations/fake.png"


@pytest.mark.asyncio
async def test_agent_character_with_fake_service():
    svc = _fake_image_service()
    agent = IllustrationAgent(image_service=svc)
    req = IllustrationRequest(
        book_id=1,
        illustration_type=IllustrationType.CHARACTER,
        book_context={"name": "レン", "appearance": "赤い瞳"},
    )
    res = await agent.run(request=req)
    assert res["status"] == "success"
    assert "レン" in res["result"].prompt


@pytest.mark.asyncio
async def test_agent_episode_with_scene_text():
    svc = _fake_image_service()
    agent = IllustrationAgent(image_service=svc)
    req = IllustrationRequest(
        book_id=1,
        illustration_type=IllustrationType.EPISODE,
        episode_number=2,
        scene_text="雪の降る村で出会った。",
    )
    res = await agent.run(request=req)
    assert res["status"] == "success"
    assert "雪" in res["result"].prompt


@pytest.mark.asyncio
async def test_agent_episode_r15_prompt_contains_keywords():
    svc = _fake_image_service()
    agent = IllustrationAgent(image_service=svc)
    req = IllustrationRequest(
        book_id=1,
        illustration_type=IllustrationType.EPISODE,
        episode_number=1,
        safety_level=SafetyLevel.R15_CONTENT,
    )
    res = await agent.run(request=req)
    assert res["status"] == "success"
    assert any(w in res["result"].prompt.lower() for w in ["r15", "artistic", "intimate"])


@pytest.mark.asyncio
async def test_agent_rejects_invalid_request():
    svc = _fake_image_service()
    agent = IllustrationAgent(image_service=svc)
    res = await agent.run(request=None)
    assert res["status"] == "error"


# ---------------------------------------------------------------------------
# Model selector
# ---------------------------------------------------------------------------


def test_resolve_model_id_fast():
    assert resolve_model_id(IllustrationModel.FAST) == "imagen-4.0-fast-generate-001"


def test_resolve_model_id_quality():
    assert resolve_model_id(IllustrationModel.QUALITY) == "imagen-4.0-generate-001"


def test_resolve_model_id_ultra():
    assert resolve_model_id(IllustrationModel.ULTRA) == "imagen-4.0-ultra-generate-001"


def test_resolve_model_id_auto():
    assert resolve_model_id(IllustrationModel.AUTO) == "imagen-4.0-fast-generate-001"


def test_resolve_model_id_unknown_falls_back_to_default():
    from config.imagen_models import get_imagen_model_id

    assert get_imagen_model_id("nonexistent") == "imagen-4.0-fast-generate-001"


@pytest.mark.asyncio
async def test_resolve_request_model_auto_episode():
    svc = _fake_image_service()
    agent = IllustrationAgent(image_service=svc)
    req = IllustrationRequest(
        book_id=1,
        illustration_type=IllustrationType.EPISODE,
        model=IllustrationModel.AUTO,
        book_context={"genre": "SF"},
    )
    res = await agent.run(request=req)
    assert res["status"] == "success"
    assert res["result"].model_used == "imagen-4.0-fast-generate-001"


@pytest.mark.asyncio
async def test_resolve_request_model_auto_cover():
    svc = _fake_image_service()
    agent = IllustrationAgent(image_service=svc)
    req = IllustrationRequest(
        book_id=1,
        illustration_type=IllustrationType.COVER,
        model=IllustrationModel.AUTO,
        book_context={"genre": "ファンタジー"},
    )
    res = await agent.run(request=req)
    assert res["status"] == "success"
    assert res["result"].model_used == "imagen-4.0-ultra-generate-001"


@pytest.mark.asyncio
async def test_resolve_request_model_auto_r15_quality():
    svc = _fake_image_service()
    agent = IllustrationAgent(image_service=svc)
    req = IllustrationRequest(
        book_id=1,
        illustration_type=IllustrationType.EPISODE,
        model=IllustrationModel.AUTO,
        safety_level=SafetyLevel.R15_CONTENT,
    )
    res = await agent.run(request=req)
    assert res["status"] == "success"
    assert res["result"].model_used == "imagen-4.0-generate-001"


# ---------------------------------------------------------------------------
# Repository (real sqlite)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_illustration_repo_create_and_list():
    import tempfile

    from sqlalchemy import create_engine

    from src.backend.database.core import DatabaseManager
    from src.backend.database.models import Base
    from src.backend.database.uow import UnitOfWork

    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    url = f"sqlite+aiosqlite:///{tmp.name}"
    sync_engine = create_engine(url.replace("sqlite+aiosqlite:///", "sqlite:///"))
    Base.metadata.create_all(sync_engine)

    db = DatabaseManager(url)
    async with UnitOfWork(db) as uow:
        # 親 book を先に作成（外部キー制約のため）
        from src.backend.database.models import Book

        uow.session.add(Book(title="test", genre="test"))
        await uow.session.flush()

        illo_id = await uow.illustrations.create_illustration(
            book_id=1,
            illustration_type="cover",
            image_url="/static/x.png",
            prompt="cover prompt",
            model="imagen-4.0-fast-generate-001",
        )
        assert illo_id > 0
        rows = await uow.illustrations.list_illustrations(book_id=1)
        assert len(rows) == 1
        assert rows[0].image_url == "/static/x.png"

        covers = await uow.illustrations.list_illustrations(book_id=1, illustration_type="cover")
        assert len(covers) == 1
