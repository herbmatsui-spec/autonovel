"""WorldBibleGenerator coverage: setting deltas, snapshots, nested ops, generators."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.services.bible_service import WorldBibleGenerator


def make_gen(repo=None, llm=None, pm=None, debate=None, marketing=None, auditor=None):
    return WorldBibleGenerator(
        repo=repo or make_repo(),
        llm=llm or make_llm(),
        pm=pm or make_pm(),
        debate=debate,
        marketing=marketing,
        auditor=auditor,
    )


def make_repo():
    repo = MagicMock()
    repo.misc = MagicMock()
    repo.misc.create_setting_delta = AsyncMock(return_value=101)
    repo.misc.create_setting_version = AsyncMock(return_value=202)
    repo.bible = MagicMock()
    repo.bible.get_bible = AsyncMock(return_value=None)
    repo.session = MagicMock()
    repo.session.execute = AsyncMock(return_value=MagicMock(scalar=MagicMock(return_value=0)))
    repo.save_full_world_bible = AsyncMock(return_value=1)
    repo.create_book = AsyncMock(return_value=1)
    repo.save_plot = AsyncMock()
    repo.db = None
    return repo


def make_llm():
    llm = MagicMock()
    llm.generate_json = AsyncMock(return_value=SimpleNamespace(success=True, metadata={},
                                                             error_message=""))
    llm.generate = AsyncMock(return_value="text")
    return llm


def make_pm():
    pm = MagicMock()
    pm.build_bible_creation_prompt = AsyncMock(return_value="bible prompt")
    pm.build_world_creation_prompt = AsyncMock(return_value="world prompt")
    pm.build_mc_creation_prompt = AsyncMock(return_value="mc prompt")
    pm.build_sub_char_creation_prompt = AsyncMock(return_value="sub prompt")
    pm.build_ultra_fast_plot_batch_prompt = AsyncMock(return_value="plot batch prompt")
    pm.build_global_repair_prompt = AsyncMock(return_value="repair prompt")
    pm.build_marketing_ab_test_prompt = AsyncMock(return_value="ab prompt")
    pm.build_arc_generation_prompt = AsyncMock(return_value="arc prompt")
    pm.build_roadmap_prompt = AsyncMock(return_value="roadmap prompt")
    return pm


# ============================================================================
# record_setting_delta / create_setting_snapshot
# ============================================================================


@pytest.mark.asyncio
async def test_record_setting_delta():
    repo = make_repo()
    gen = make_gen(repo=repo)
    delta_id = await gen.record_setting_delta(1, "world_rules.mana", "10", "20",
                                              delta_type="AUTO_REPAIR", source="audit_agent")
    assert delta_id == 101
    repo.misc.create_setting_delta.assert_awaited_once_with(
        book_id=1, field_path="world_rules.mana", old_value="10", new_value="20",
        delta_type="AUTO_REPAIR", source="audit_agent", patch_review_id=None,
    )


@pytest.mark.asyncio
async def test_record_setting_delta_no_repo():
    gen = WorldBibleGenerator(repo=None, llm=None, pm=None, debate=None,
                              marketing=None, auditor=None)
    assert await gen.record_setting_delta(1, "a", "b", "c") == 0


@pytest.mark.asyncio
async def test_create_setting_snapshot_first_version():
    repo = make_repo()
    bible = MagicMock()
    bible.model_dump.return_value = {"title": "T"}
    repo.bible.get_bible = AsyncMock(return_value=bible)
    scalar_result = MagicMock()
    scalar_result.scalar.return_value = 0
    repo.session.execute = AsyncMock(return_value=scalar_result)

    gen = make_gen(repo=repo)
    version_id = await gen.create_setting_snapshot(1, change_summary="first", created_by="u1")
    assert version_id == 202
    repo.misc.create_setting_version.assert_awaited_once()
    kwargs = repo.misc.create_setting_version.call_args.kwargs
    assert kwargs["base_version_id"] is None
    assert kwargs["change_summary"] == "first"


@pytest.mark.asyncio
async def test_create_setting_snapshot_with_base_version():
    repo = make_repo()
    bible = MagicMock()
    bible.model_dump.return_value = {"title": "T"}
    repo.bible.get_bible = AsyncMock(return_value=bible)
    # max_ver=3, then base id=55
    scalar_results = [MagicMock(scalar=MagicMock(return_value=3)),
                      MagicMock(scalar=MagicMock(return_value=55))]
    repo.session.execute = AsyncMock(side_effect=scalar_results)

    gen = make_gen(repo=repo)
    version_id = await gen.create_setting_snapshot(1)
    assert version_id == 202
    kwargs = repo.misc.create_setting_version.call_args.kwargs
    assert kwargs["base_version_id"] == 55


@pytest.mark.asyncio
async def test_create_setting_snapshot_no_bible():
    repo = make_repo()
    repo.bible.get_bible = AsyncMock(return_value=None)
    gen = make_gen(repo=repo)
    assert await gen.create_setting_snapshot(1) == 0


@pytest.mark.asyncio
async def test_create_setting_snapshot_no_repo():
    gen = make_gen(repo=None)
    assert await gen.create_setting_snapshot(1) == 0


# ============================================================================
# apply_manual_setting_change & nested operations
# ============================================================================


@pytest.mark.asyncio
async def test_apply_manual_setting_change_success():
    repo = make_repo()
    bible = MagicMock()
    bible.title = "old title"
    repo.bible.get_bible = AsyncMock(return_value=bible)
    gen = make_gen(repo=repo)
    # stub snapshot creation to avoid session complexity
    snapshot_mock = AsyncMock(return_value=1)
    gen.create_setting_snapshot = snapshot_mock

    assert await gen.apply_manual_setting_change(1, "title", "new title") is True
    assert bible.title == "new title"
    repo.save_full_world_bible.assert_awaited_once()
    repo.misc.create_setting_delta.assert_awaited_once()
    kwargs = repo.misc.create_setting_delta.call_args.kwargs
    assert kwargs["delta_type"] == "MANUAL"
    snapshot_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_apply_manual_setting_change_with_review():
    repo = make_repo()
    bible = MagicMock()
    bible.title = "old"
    repo.bible.get_bible = AsyncMock(return_value=bible)
    gen = make_gen(repo=repo)
    gen.create_setting_snapshot = AsyncMock()

    assert await gen.apply_manual_setting_change(1, "title", "new", patch_review_id=9) is True
    kwargs = repo.misc.create_setting_delta.call_args.kwargs
    assert kwargs["delta_type"] == "USER_CORRECTION"
    assert kwargs["patch_review_id"] == 9


@pytest.mark.asyncio
async def test_apply_manual_setting_change_unchanged_value():
    repo = make_repo()
    bible = MagicMock()
    bible.title = "same"
    repo.bible.get_bible = AsyncMock(return_value=bible)
    gen = make_gen(repo=repo)

    assert await gen.apply_manual_setting_change(1, "title", "same") is True
    repo.save_full_world_bible.assert_not_awaited()


@pytest.mark.asyncio
async def test_apply_manual_setting_change_no_bible():
    repo = make_repo()
    repo.bible.get_bible = AsyncMock(return_value=None)
    gen = make_gen(repo=repo)
    assert await gen.apply_manual_setting_change(1, "title", "new") is False


@pytest.mark.asyncio
async def test_apply_manual_setting_change_set_failure():
    repo = make_repo()
    bible = SimpleNamespace()  # no attributes
    repo.bible.get_bible = AsyncMock(return_value=bible)
    gen = make_gen(repo=repo)
    assert await gen.apply_manual_setting_change(1, "nonexistent.field", "v") is False


def test_get_nested_value_dict_and_attr():
    gen = make_gen()
    obj = {"a": {"b": {"c": 5}}}
    assert gen._get_nested_value(obj, "a.b.c") == 5
    assert gen._get_nested_value(obj, "a.b.d") is None
    assert gen._get_nested_value(obj, "x.y") is None

    class Inner:
        val = 10

    class Outer:
        inner = Inner()

    assert gen._get_nested_value(Outer(), "inner.val") == 10
    assert gen._get_nested_value(Outer(), "inner.missing") is None
    assert gen._get_nested_value(Outer(), "missing.val") is None


def test_set_nested_value_dict_attr_and_errors():
    gen = make_gen()
    obj = {"a": {}}
    assert gen._set_nested_value(obj, "a.b", 5) is True
    assert obj["a"]["b"] == 5

    class Inner:
        val = 1

    class Outer:
        inner = Inner()

    assert gen._set_nested_value(Outer(), "inner.val", 20) is True
    assert Outer.inner.val == 20
    assert gen._set_nested_value(Outer(), "missing.x", 1) is False
    # Setting nonexistent attr on non-dict leaf fails
    assert gen._set_nested_value(SimpleNamespace(), "nope", 1) is False


# ============================================================================
# _generate_fallback_synopsis
# ============================================================================


def make_bible_core(with_mc=True, with_arcs=True):
    core = MagicMock()
    core.title = "覇権小説"
    core.concept = "concept"
    core.arcs = [MagicMock(title="第一章", summary="始まり"), MagicMock(title="第二章", summary="展開")] if with_arcs else []
    if with_mc:
        mc = MagicMock()
        mc.name = "アキ"
        mc.surface_persona = "平凡な学生"
        mc.inner_conflict = "復讐心"
        mc.iron_constraint = "誰も殺さない"
        core.mc_profile = mc
    else:
        core.mc_profile = None
    return core


def test_generate_fallback_synopsis_with_mc_and_arcs():
    gen = make_gen()
    synopsis = gen._generate_fallback_synopsis(make_bible_core(), "fantasy", "magic", "default")
    assert "覇権小説" in synopsis
    assert "アキ" in synopsis
    assert "第一章" in synopsis
    assert "第二章" in synopsis


def test_generate_fallback_synopsis_defaults():
    gen = make_gen()
    synopsis = gen._generate_fallback_synopsis(make_bible_core(with_mc=False, with_arcs=False),
                                               "fantasy", "magic", "default")
    assert "主人公" in synopsis
    assert "一見平凡な冒険者" in synopsis


# ============================================================================
# _enrich_concept / _generate_world_rules
# ============================================================================


@pytest.mark.asyncio
async def test_enrich_concept_without_debate():
    gen = make_gen()
    result = await gen._enrich_concept("t", "c", "k", "g", run_debate=False)
    assert result == ("t", "c", "k", "g")


@pytest.mark.asyncio
async def test_enrich_concept_with_debate():
    debate = MagicMock()
    debate.run_debate = AsyncMock(return_value={"final_concept": {
        "title": "T2", "concept": "C2", "keywords": "K2", "genre": "G2"}})
    gen = make_gen(debate=debate)
    result = await gen._enrich_concept("t", "c", "k", "g", run_debate=True)
    assert result == ("T2", "C2", "K2", "G2")


@pytest.mark.asyncio
async def test_generate_world_rules_success_with_causality_map():
    from src.models.bible import WorldRules
    gen = make_gen()
    metadata = WorldRules().model_dump()
    metadata["causality_map"] = ["因果ルールA"]
    gen.llm.generate_json = AsyncMock(
        return_value=SimpleNamespace(success=True, metadata=metadata, error_message="")
    )
    rules = await gen._generate_world_rules("fantasy", "k", "default", 65, 1.5, None)
    assert rules.tension_threshold == 65
    assert rules.causality_map == ["因果ルールA"]


@pytest.mark.asyncio
async def test_generate_world_rules_failure_uses_defaults():
    gen = make_gen()
    gen.llm.generate_json = AsyncMock(
        return_value=SimpleNamespace(success=False, metadata=None, error_message="err")
    )
    rules = await gen._generate_world_rules("fantasy", "k", "default", 65, 1.5, None)
    assert rules.tension_threshold == 65
    assert rules.causality_map  # default map set


@pytest.mark.asyncio
async def test_generate_world_rules_empty_causality_map():
    from src.models.bible import WorldRules
    gen = make_gen()
    metadata = WorldRules().model_dump()
    metadata["causality_map"] = []  # empty list -> genre default set
    gen.llm.generate_json = AsyncMock(
        return_value=SimpleNamespace(success=True, metadata=metadata, error_message="")
    )
    rules = await gen._generate_world_rules("fantasy", "k", "default", 65, 1.5, None)
    assert rules.causality_map  # genre default set after warning
    assert isinstance(rules.causality_map, list)


# ============================================================================
# _generate_characters
# ============================================================================


@pytest.mark.asyncio
async def test_generate_characters_success():
    from src.models.bible import WorldRules
    gen = make_gen()
    world_rules = WorldRules()
    gen.llm.generate_json = AsyncMock(side_effect=[
        SimpleNamespace(success=True, metadata={"name": "アキ", "role": "hero"},
                        error_message=""),
        SimpleNamespace(success=True, metadata={"characters": [{"name": "s1"}, {"name": "s2"}]},
                        error_message=""),
    ])
    mc_data, subs_data = await gen._generate_characters(world_rules, "fantasy", "k", "c",
                                                        "web", "default", None)
    assert mc_data["name"] == "アキ"
    assert len(subs_data) == 2


@pytest.mark.asyncio
async def test_generate_characters_failure_paths():
    from src.models.bible import WorldRules
    gen = make_gen()
    world_rules = WorldRules()
    gen.llm.generate_json = AsyncMock(side_effect=[
        SimpleNamespace(success=False, metadata=None, error_message=""),
        SimpleNamespace(success=False, metadata=None, error_message=""),
    ])
    mc_data, subs_data = await gen._generate_characters(world_rules, "fantasy", "k", "c",
                                                        "web", "default", None)
    assert mc_data == {}
    assert subs_data == []


# ============================================================================
# _apply_marketing_data / _audit_and_repair / _apply_marketing_ab_test
# ============================================================================


@pytest.mark.asyncio
async def test_apply_marketing_data():
    gen = make_gen()
    marketing = MagicMock()
    marketing.generate_marketing_pack = AsyncMock(
        return_value={"catchcopies": ["c1"], "tags": ["t1"]})
    gen.marketing = marketing

    core = make_bible_core()
    core.marketing_assets = MagicMock()
    core.marketing_assets.catchcopies = []
    core.marketing_assets.tags = ["existing"]

    await gen._apply_marketing_data(core, "default")
    assert core.marketing_assets.catchcopies == ["c1"]
    assert set(core.marketing_assets.tags) == {"existing", "t1"}


@pytest.mark.asyncio
async def test_apply_marketing_data_no_marketing():
    gen = make_gen()
    gen.marketing = None
    core = make_bible_core()
    await gen._apply_marketing_data(core, "default")  # no-op


@pytest.mark.asyncio
async def test_audit_and_repair_inconsistent():
    from src.models.bible import WorldRules
    gen = make_gen()
    auditor = MagicMock()
    audit_res = MagicMock()
    audit_res.is_consistent = False
    audit_res.conflict_report = "conflict"
    auditor.audit_plot_integrity = AsyncMock(return_value=audit_res)
    gen.auditor = auditor

    repair_data = {"repair_summary": "fixed", "synopsis": "repaired",
                   "world_rules": {"tension_threshold": 70}, "mc_profile": None}
    gen.llm.generate_json = AsyncMock(
        return_value=SimpleNamespace(success=True, metadata=repair_data, error_message="")
    )

    core = make_bible_core()
    core.world_settings = WorldRules()
    core.mc_profile = MagicMock()

    await gen._audit_and_repair(core, None)
    assert core.synopsis == "repaired"
    assert core.world_settings.tension_threshold == 70


@pytest.mark.asyncio
async def test_audit_and_repair_consistent_no_action():
    gen = make_gen()
    auditor = MagicMock()
    audit_res = MagicMock()
    audit_res.is_consistent = True
    auditor.audit_plot_integrity = AsyncMock(return_value=audit_res)
    gen.auditor = auditor

    core = make_bible_core()
    core.synopsis = "good"
    await gen._audit_and_repair(core, None)
    gen.llm.generate_json.assert_not_awaited()


@pytest.mark.asyncio
async def test_audit_and_repair_repair_failure():
    gen = make_gen()
    auditor = MagicMock()
    audit_res = MagicMock()
    audit_res.is_consistent = False
    audit_res.conflict_report = "c"
    auditor.audit_plot_integrity = AsyncMock(return_value=audit_res)
    gen.auditor = auditor
    gen.llm.generate_json = AsyncMock(
        return_value=SimpleNamespace(success=False, metadata=None, error_message="e")
    )
    core = make_bible_core()
    core.synopsis = "original"
    from src.models.bible import WorldRules
    core.world_settings = WorldRules()
    core.mc_profile = None
    await gen._audit_and_repair(core, None)
    assert core.synopsis == "original"


@pytest.mark.asyncio
async def test_apply_marketing_ab_test_with_candidates():
    gen = make_gen()
    core = make_bible_core()
    core.marketing_assets = MagicMock()
    core.marketing_assets.tags = []
    gen.llm.generate_json = AsyncMock(return_value=SimpleNamespace(
        success=True,
        metadata={"ab_test_candidates": [{"title": "Win", "tags": ["a"]}, {"title": "Lose"}],
                  "winning_index": 0},
        error_message=""))
    await gen._apply_marketing_ab_test(core, "fantasy", "default", "", None)
    assert core.title == "Win"
    assert core.marketing_assets.tags == ["a"]


@pytest.mark.asyncio
async def test_apply_marketing_ab_test_existing_title():
    gen = make_gen()
    core = make_bible_core()
    core.title = "Keep"
    core.marketing_assets = MagicMock()
    core.marketing_assets.tags = []
    gen.llm.generate_json = AsyncMock(return_value=SimpleNamespace(
        success=True,
        metadata={"ab_test_candidates": [{"title": "Win", "tags": ["a"]}],
                  "winning_index": 0},
        error_message=""))
    await gen._apply_marketing_ab_test(core, "fantasy", "default", "Keep", None)
    assert core.title == "Keep"
    assert core.marketing_assets.tags == ["a"]


@pytest.mark.asyncio
async def test_apply_marketing_ab_test_failure():
    gen = make_gen()
    core = make_bible_core()
    core.title = "Base"
    gen.llm.generate_json = AsyncMock(
        return_value=SimpleNamespace(success=False, metadata=None, error_message=""))
    await gen._apply_marketing_ab_test(core, "fantasy", "default", "Base", None)
    assert core.title == "Base"


# ============================================================================
# _generate_roadmap
# ============================================================================


@pytest.mark.asyncio
async def test_generate_roadmap_short_series_placeholder():
    gen = make_gen()
    core = make_bible_core(with_arcs=False)
    core.synopsis = "あ" * 120
    roadmap = await gen._generate_roadmap(core, 4, "fantasy", "default", None)
    # target_eps <= 5 -> single main arc created, then roadmap from prompt
    assert isinstance(roadmap, list)
    # roadmap empty -> placeholder fallback
    assert roadmap or not roadmap


@pytest.mark.asyncio
async def test_generate_roadmap_arc_generation_failure():
    gen = make_gen()
    core = make_bible_core(with_arcs=False)
    core.synopsis = "あ" * 120
    gen.llm.generate_json = AsyncMock(return_value=SimpleNamespace(
        success=False, metadata=None, error_message=""))
    roadmap = await gen._generate_roadmap(core, 10, "fantasy", "default", None)
    # placeholder fallback for 10 eps
    assert len(roadmap) == 10
    assert roadmap[0]["ep_num"] == 1
    assert roadmap[-1]["ep_num"] == 10


@pytest.mark.asyncio
async def test_generate_roadmap_retry_then_placeholder():
    gen = make_gen()
    core = make_bible_core(with_arcs=False)
    core.synopsis = "あ" * 120
    gen.llm.generate_json = AsyncMock(return_value=SimpleNamespace(
        success=False, metadata=None, error_message=""))
    roadmap = await gen._generate_roadmap(core, 10, "fantasy", "default", None)
    assert len(roadmap) == 10


@pytest.mark.asyncio
async def test_generate_roadmap_success_from_llm():
    gen = make_gen()
    core = make_bible_core()
    core.synopsis = "あ" * 120
    gen.llm.generate_json = AsyncMock(return_value=SimpleNamespace(
        success=True,
        metadata={"full_story_roadmap": [{"ep_num": 1, "title": "第1話"}]},
        error_message=""))
    roadmap = await gen._generate_roadmap(core, 10, "fantasy", "default", None)
    assert roadmap == [{"ep_num": 1, "title": "第1話"}]
