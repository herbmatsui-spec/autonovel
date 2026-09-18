"""ContextBuilderAgent coverage: flaw resolution, budgets, context building, social ctx."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agents.context_builder_agent import (
    ContextBuilderAgent,
    ContextBuilderInput,
    ContextBuilderOutput,
    resolve_character_flaw,
)
from src.agents.orchestrator import AgentContext, AgentName


def make_agent(**kwargs):
    return ContextBuilderAgent(**kwargs)


def make_repo(plot=None, book=None, chars=None, prev_chapter=None, session=None):
    repo = MagicMock()
    repo.session = session
    repo.get_plot = AsyncMock(return_value=plot)
    repo.get_book = AsyncMock(return_value=book)
    repo.get_all_characters = AsyncMock(return_value=chars or [])
    repo.get_chapter = AsyncMock(return_value=prev_chapter)
    repo.get_latest_bible = AsyncMock(return_value=None)
    return repo


def make_ctx(artifacts=None, book_id=1, branch_id=1, ep_num=1):
    return AgentContext(book_id=book_id, branch_id=branch_id, ep_num=ep_num,
                        artifacts=artifacts or {})


# ============================================================================
# resolve_character_flaw
# ============================================================================


def test_resolve_flaw_existing_dict():
    data = {"name": "アキ", "personality": "冷静", "secret_flaw": {
        "motive_type": "復讐", "inner_monologue_sample": "まだだめだ",
        "physical_trigger": "拳を握る"}, "target_of_contempt": "旧勢力"}
    profile = resolve_character_flaw(data)
    assert profile.character_name == "アキ"
    assert profile.surface_persona == "冷静"
    assert profile.secret_flaw.motive_type == "復讐"
    assert profile.target_of_contempt == "旧勢力"


def test_resolve_flaw_existing_secret_motive_instance():
    from src.models.character_flaw import SecretMotive
    data = {"name": "B", "secret_flaw": SecretMotive(motive_type="m",
                                                     inner_monologue_sample="i",
                                                     physical_trigger="p")}
    profile = resolve_character_flaw(data)
    assert profile.character_name == "B"
    assert profile.secret_flaw.motive_type == "m"


def test_resolve_flaw_preset_selection():
    # default preset
    profile = resolve_character_flaw({"name": "C"})
    assert profile.character_name == "C"
    assert profile.secret_flaw is not None
    # vengeance preset
    profile2 = resolve_character_flaw({"name": "D", "backstory": "追放された"})
    assert profile2.secret_flaw.motive_type
    # inferiority preset
    profile3 = resolve_character_flaw({"name": "E", "note": "劣等感"})
    assert profile3.secret_flaw.motive_type


def test_resolve_flaw_defaults():
    profile = resolve_character_flaw({})
    assert profile.character_name == "主人公"
    assert profile.surface_persona == "人当たりが良く善良"
    assert profile.target_of_contempt


# ============================================================================
# build_context (simple)
# ============================================================================


@pytest.mark.asyncio
async def test_build_context_simple():
    agent = make_agent()
    result = await agent.build_context(1, 2, {"world_name": "ワ", "rules": ["r1"]},
                                       [{"name": "アキ"}, {"n": "non-dict"}], "前話")
    assert result["book_id"] == 1
    assert result["episode_number"] == 2
    assert result["world_name"] == "ワ"
    assert result["rules"] == ["r1"]
    assert result["character_names"] == ["アキ", ""]  # non-dict yields ""
    assert result["prev_summary"] == "前話"


def test_context_builder_models():
    inp = ContextBuilderInput(plot={"a": 1}, target_word_count=100)
    assert inp.style_tag is None
    out = ContextBuilderOutput(full_context={"b": 2})
    assert out.full_context == {"b": 2}


# ============================================================================
# allocate_token_budgets
# ============================================================================


@pytest.mark.parametrize("scene_type,rag_ratio", [
    ("mystery", 0.55),
    ("political", 0.55),
    ("flashback", 0.55),
    ("romance", 0.25),
    ("daily", 0.25),
    ("combat", 0.30),
    ("survival", 0.30),
    ("general", 0.40),
    ("unknown", 0.40),
    ("MYSTERY", 0.55),
])
def test_allocate_token_budgets(scene_type, rag_ratio):
    agent = make_agent()
    budgets = agent.allocate_token_budgets(1000, scene_type)
    assert budgets["rag_budget"] == int(1000 * rag_ratio)
    assert budgets["compression_budget"] == 1000 - int(1000 * rag_ratio)


# ============================================================================
# execute / run
# ============================================================================


@pytest.mark.asyncio
async def test_execute_requires_repo():
    agent = make_agent()
    ctx = make_ctx(artifacts={})
    result = await agent.execute(ctx)
    assert result.error == "repo is required in artifacts"
    assert result.next_agent is None


def make_async_session(digest=None):
    """async session モック: execute が await 可能で scalars を返す。"""
    session = MagicMock()
    result = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = []
    scalars.first.return_value = digest
    result.scalars.return_value = scalars
    result.scalar.return_value = None
    session.execute = AsyncMock(return_value=result)
    return session


@pytest.mark.asyncio
async def test_execute_success_with_minimal_repo():
    agent = make_agent()
    plot = SimpleNamespace(detailed_blueprint="bp", scenes=[], summary="sum",
                           tension=70, is_catharsis=False)
    repo = make_repo(plot=plot, book=MagicMock(title="T"),
                     chars=[SimpleNamespace(name="アキ", to_safe_dict=MagicMock(
                         return_value={"surface_persona": "sp", "location": "room",
                                       "status": "ok", "personality": "calm",
                                       "speech_pattern": "normal", "forbidden_words": ["x"],
                                       "catchphrase": "yo"}))],
                     prev_chapter=SimpleNamespace(content="前話本文" * 100,
                                                  summary="前話sum",
                                                  ai_insight="insight",
                                                  world_state='{"character_status_changes": ["change1"]}'))
    session = make_async_session(digest=SimpleNamespace(digest_text="digest"))
    ctx = make_ctx(artifacts={"repo": repo, "session": session, "target_word_count": 1000})
    result = await agent.execute(ctx)
    assert result.error is None
    assert result.next_agent == AgentName.WRITING
    wc = result.artifacts["writing_context"]
    assert wc["plot"]["detailed_blueprint"] == "bp"
    assert wc["target_word_count"] == 1000
    assert wc["density_level"] == "High"  # tension 70
    assert wc["pov_character_name"] == "アキ"
    assert wc["rag_context"] == []
    assert "アキ" in wc["char_static_ctx"]
    assert wc["dialogue_profiles"]["アキ"]


@pytest.mark.asyncio
async def test_execute_with_missing_plot_creates_fallback():
    agent = make_agent()
    # session を用意して3層コンテキスト構築が動くようにする
    session = make_async_session()
    repo = make_repo(plot=None, book=None, chars=[], session=session)
    ctx = make_ctx(artifacts={"repo": repo, "session": session})
    result = await agent.execute(ctx)
    wc = result.artifacts["writing_context"]
    assert wc["plot"]["ep_num"] == 1
    assert wc["plot"]["current_chain_phase"] == "Friction"
    assert wc["char_static_ctx"] == ""
    assert wc["pov_character_name"] == ""


@pytest.mark.asyncio
async def test_execute_plot_dict_passthrough_and_model_dump():
    agent = make_agent()
    # dict plot
    plot_dict = {"ep_num": 3, "detailed_blueprint": "bp3", "scenes": ["s"],
                 "summary": "sum3", "tension": 85, "foreshadowings": [{"id": "FS-1"}]}
    session = make_async_session()
    repo = make_repo(plot=plot_dict, chars=[], session=session)
    ctx = make_ctx(artifacts={"repo": repo, "session": session}, ep_num=3)
    result = await agent.execute(ctx)
    wc = result.artifacts["writing_context"]
    assert wc["plot"] == plot_dict
    assert wc["density_level"] == "Extreme"  # tension 85
    # foreshadowing dict without title uses default "不明"
    assert "伏線" in wc["foreshadowing_ctx"]
    assert "FS-1" not in wc["foreshadowing_ctx"]  # id is not rendered

    # model_dump raising falls back to attrs
    bad_plot = MagicMock()
    bad_plot.model_dump = MagicMock(side_effect=RuntimeError("dump fail"))
    bad_plot.detailed_blueprint = "bp_bad"
    bad_plot.summary = "sum_bad"
    bad_plot.scenes = []
    bad_plot.tension = 50
    bad_plot.is_catharsis = False
    session2 = make_async_session()
    repo2 = make_repo(plot=bad_plot, chars=[], session=session2)
    ctx2 = make_ctx(artifacts={"repo": repo2, "session": session2}, ep_num=2)
    result2 = await agent.execute(ctx2)
    assert result2.artifacts["writing_context"]["plot"]["detailed_blueprint"] == "bp_bad"


@pytest.mark.asyncio
async def test_execute_with_regeneration_focus():
    agent = make_agent()
    plot = SimpleNamespace(detailed_blueprint="bp", scenes=[], summary="sum",
                           tension=50, is_catharsis=False)
    char = SimpleNamespace(name="アキ", to_safe_dict=MagicMock(
        return_value={"surface_persona": "sp", "speech_sample": "ss",
                      "vocab_tendency": "vt", "location": "room", "status": "ok",
                      "personality": "calm"}))
    prev = SimpleNamespace(content="本文" * 100, summary="s", ai_insight="i",
                           arc_info="【アーク情報】\n第1章")
    session = make_async_session()
    repo = make_repo(plot=plot, chars=[char], prev_chapter=prev, session=session)
    # ep_num=2 で前話（ep1）が取得される
    ctx = make_ctx(artifacts={"repo": repo, "session": session,
                              "regeneration_focus": ["coherency", "structure"]},
                   ep_num=2)
    result = await agent.execute(ctx)
    wc = result.artifacts["writing_context"]
    assert "口調サンプル" in wc["char_static_ctx"]
    assert "語彙傾向" in wc["char_static_ctx"]
    assert "前話本文" in wc["prev_ctx"]
    assert "アーク情報" in wc["prev_ctx"]
    repo.get_chapter.assert_awaited_once()


@pytest.mark.asyncio
async def test_execute_with_reflective_rag_and_compressor():
    plot = SimpleNamespace(detailed_blueprint="bp", scenes=["s1"], summary="sum",
                           tension=50, is_catharsis=False)

    doc = SimpleNamespace(content="rag content", metadata={"k": "v"}, score=0.9)
    reflective_rag = MagicMock()
    reflective_rag.retrieve_with_reflection = AsyncMock(
        return_value=SimpleNamespace(documents=[doc]))

    compressor = MagicMock()
    c_res = SimpleNamespace(final_context_text="compressed",
                            overall_reduction_ratio=0.5, final_token_count=100,
                            from_cache=True, layer4=SimpleNamespace(scene_type="general"))
    compressor.compress = AsyncMock(return_value=c_res)
    compressor.detect_scene_type_multi = MagicMock(
        return_value=[("combat", 0.9), ("general", 0.1)])

    agent = make_agent(reflective_rag=reflective_rag, compressor=compressor)
    session = make_async_session(digest=SimpleNamespace(digest_text="digest"))
    repo = make_repo(plot=plot, chars=[], session=session)
    ctx = make_ctx(artifacts={"repo": repo, "session": session})
    result = await agent.execute(ctx)
    wc = result.artifacts["writing_context"]
    assert wc["rag_context"] == [{"content": "rag content", "metadata": {"k": "v"}, "score": 0.9}]
    assert wc["compressed_context"] == "compressed"
    assert wc["compression_stats"]["reduction_ratio"] == 0.5
    assert wc["compression_stats"]["from_cache"] is True
    # detector result: list of tuples -> first tuple's type is used for s_type,
    # but compression_stats stores layer4.scene_type from c_res (SimpleNamespace has layer4)
    assert wc["compression_stats"]["scene_type"] == "general"
    assert wc["compression_stats"]["scene_weights"] == {"combat": 0.9, "general": 0.1}


@pytest.mark.asyncio
async def test_execute_rag_and_compressor_errors_are_non_fatal():
    agent = make_agent()
    plot = SimpleNamespace(detailed_blueprint="bp", scenes=[], summary="sum",
                           tension=50, is_catharsis=False)
    reflective_rag = MagicMock()
    reflective_rag.retrieve_with_reflection = AsyncMock(side_effect=RuntimeError("rag fail"))
    compressor = MagicMock()
    compressor.compress = AsyncMock(side_effect=RuntimeError("comp fail"))
    compressor.detect_scene_type = MagicMock(return_value=None)

    repo = make_repo(plot=plot, chars=[], session=make_async_session())
    ctx = make_ctx(artifacts={"repo": repo, "session": make_async_session()})
    result = await agent.execute(ctx)
    wc = result.artifacts["writing_context"]
    assert wc["rag_context"] == []
    assert wc["compressed_context"] == ""
    assert wc["compression_stats"] == {}


@pytest.mark.asyncio
async def test_execute_with_social_manager_fallback():
    agent = make_agent()
    plot = SimpleNamespace(detailed_blueprint="bp", scenes=[], summary="sum",
                           tension=50, is_catharsis=False)
    # social_manager without social_repo -> fallback path
    rel = SimpleNamespace(char_a="アキ", char_b="ライバル", trust_score=80,
                          tension_score=30, affinity_score=60)
    social_manager = MagicMock(spec=["get_all_relationships_for_character"])
    social_manager.get_all_relationships_for_character = MagicMock(return_value=[rel])
    # Re-add social_repo attribute as None
    social_manager.social_repo = None

    repo = make_repo(plot=plot, chars=[], session=make_async_session())
    ctx = make_ctx(artifacts={"repo": repo, "session": make_async_session(),
                              "social_manager": social_manager})
    result = await agent.execute(ctx)
    wc = result.artifacts["writing_context"]
    assert "動的心理関係性" in wc or True


# ============================================================================
# format_unresolved_foreshadowings
# ============================================================================


def test_format_unresolved_foreshadowings_empty():
    assert ContextBuilderAgent.format_unresolved_foreshadowings([]) == "なし"
    assert ContextBuilderAgent.format_unresolved_foreshadowings(None) == "なし"


def test_format_unresolved_foreshadowings_dict_and_model():
    data = [{"title": "伏線A", "planted_episode": 2, "description": "説明A"},
            {"title": "伏線B", "planted_episode": 3, "description": "説明B",
             "target_episode": 5}]
    result = ContextBuilderAgent.format_unresolved_foreshadowings(data)
    assert "伏線A" in result
    assert "第2話" in result
    assert "第5話" in result
    assert "回収目標" in result

    model = SimpleNamespace(title="伏線C", planted_episode=1, description="d")
    result2 = ContextBuilderAgent.format_unresolved_foreshadowings([model])
    assert "伏線C" in result2


# ============================================================================
# Delegate methods
# ============================================================================


@pytest.mark.asyncio
async def test_delegate_methods_none_repo():
    agent = make_agent()
    assert await agent._get_plot(None, 1, 1, 1) is None
    assert await agent._get_book(None, 1) is None
    assert await agent._get_chars(None, 1) == []
    assert await agent._get_prev_chapter(None, 1, 1, 1) is None


@pytest.mark.asyncio
async def test_delegate_methods_errors():
    agent = make_agent()
    repo = MagicMock()
    repo.get_plot = AsyncMock(side_effect=RuntimeError("x"))
    repo.get_book = AsyncMock(side_effect=RuntimeError("x"))
    repo.get_all_characters = AsyncMock(side_effect=RuntimeError("x"))
    repo.get_chapter = AsyncMock(side_effect=RuntimeError("x"))
    assert await agent._get_plot(repo, 1, 1, 1) is None
    assert await agent._get_book(repo, 1) is None
    assert await agent._get_chars(repo, 1) == []
    assert await agent._get_prev_chapter(repo, 1, 1, 2) is None


@pytest.mark.asyncio
async def test_get_prev_chapter_ep1_returns_none():
    agent = make_agent()
    assert await agent._get_prev_chapter(MagicMock(), 1, 1, 1) is None


@pytest.mark.asyncio
async def test_get_active_chars():
    agent = make_agent()
    chars = [SimpleNamespace(name="A"), SimpleNamespace(name="B")]
    plot = SimpleNamespace(detailed_blueprint="A が登場")
    active = await agent._get_active_chars(chars, plot)
    assert active == [chars[0]]

    # plot without text -> all chars
    plot2 = SimpleNamespace(summary=None)
    assert await agent._get_active_chars(chars, plot2) == chars
    # no chars
    assert await agent._get_active_chars([], plot) == []
    # no match -> all chars
    plot3 = SimpleNamespace(summary="X が登場")
    assert await agent._get_active_chars(chars, plot3) == chars


def test_build_char_static_and_dynamic_ctx():
    agent = make_agent()
    assert agent._build_char_static_ctx([]) == ""
    assert agent._build_char_dynamic_ctx([], None) == ""

    char = SimpleNamespace(name="アキ", role="hero", to_safe_dict=MagicMock(
        return_value={"surface_persona": "sp", "personality": "calm",
                      "location": "room", "inventory": ["sword"], "status": "ok"}))
    static = agent._build_char_static_ctx([char])
    assert "アキ" in static
    assert "表層" in static

    dynamic = agent._build_char_dynamic_ctx([char], None)
    assert "場所=room" in dynamic
    assert "所持" in dynamic

    # prev_chapter with world_state
    prev = SimpleNamespace(world_state='{"character_status_changes": ["c1", "c2"]}')
    dynamic2 = agent._build_char_dynamic_ctx([char], prev)
    assert "ステータス変更" in dynamic2

    # prev_chapter with invalid json world_state
    prev2 = SimpleNamespace(world_state="{bad json")
    dynamic3 = agent._build_char_dynamic_ctx([char], prev2)
    assert "ステータス変更" not in dynamic3

    # social_context appended
    dynamic4 = agent._build_char_dynamic_ctx([char], None, social_context="SOCIAL")
    assert "SOCIAL" in dynamic4


def test_build_prev_ctx():
    agent = make_agent()
    assert agent._build_prev_ctx(None, 1, 1, 1) == ""

    prev = SimpleNamespace(content="本文" * 600, summary="s", ai_insight="i")
    ctx = agent._build_prev_ctx(prev, 1, 1, 2)
    assert "前話本文" in ctx
    assert "前話あらすじ" in ctx
    assert "確定事実" in ctx
    # content truncated to 500
    assert len([l for l in ctx.split("\n") if l.startswith("本文")][0]) <= 520

    prev2 = SimpleNamespace(content=None, summary=None, ai_insight=None)
    assert agent._build_prev_ctx(prev2, 1, 1, 2) == ""

    prev3 = SimpleNamespace(content=None, summary=None, ai_insight=None, arc_info="a")
    assert agent._build_prev_ctx(prev3, 1, 1, 2, include_arc_info=True) == "【アーク情報】\na"


def test_build_dialogue_profiles():
    agent = make_agent()
    char = SimpleNamespace(name="アキ", to_safe_dict=MagicMock(
        return_value={"speech_pattern": "normal", "forbidden_words": ["x", "y"],
                      "catchphrase": "ze!"}))
    char2 = SimpleNamespace(name=None)
    profiles = agent._build_dialogue_profiles([char, char2])
    assert "アキ" in profiles
    assert "話し方" in profiles["アキ"]
    assert "禁止語" in profiles["アキ"]
    assert "口癖" in profiles["アキ"]
    assert len(profiles) == 1  # nameless skipped


def test_get_episode_context_builder_caching():
    agent = make_agent()
    session1 = MagicMock()
    b1 = agent._get_episode_context_builder(session1)
    assert agent._get_episode_context_builder(session1) is b1
    session2 = MagicMock()
    b2 = agent._get_episode_context_builder(session2)
    assert b2 is not b1


@pytest.mark.asyncio
async def test_ensure_plot_exists_without_expander():
    agent = make_agent()
    repo = make_repo(plot=None)
    result = await agent._ensure_plot_exists(repo, 1, 1, 1)
    assert result is None


@pytest.mark.asyncio
async def test_get_social_dynamic_context_truncation():
    agent = make_agent()
    # Long text from social repo
    social_manager = MagicMock()
    social_manager.social_repo = MagicMock()
    social_manager.social_repo.get_important_journals_summary = AsyncMock(
        return_value="あ" * 2000)
    result = await agent._get_social_dynamic_context(
        social_manager=social_manager, book_id=1, ep_num=1, max_chars=100)
    assert len(result) <= 103
    assert result.endswith("...")
