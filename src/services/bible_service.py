import asyncio
import json
import logging
from typing import Any, Dict, List, Tuple

from config import MODEL_PLANNING, MODEL_PLOT_EXPANSION
from config.domain_profile_manager import DomainProfileService
from src.backend.engine_utils import safe_get, safe_model_validate
from src.models import (
    ArcBlueprint,
    ArcList,
    CharacterRegistry,
    GlobalLogicRepairResult,
    RoadmapList,
    UltraFastPlotBatch,
    UltraFastWorldBible,
    WorldBible,
    WorldBibleCore,
    WorldRules,
)
from src.models.planning_config import PlanningConfig
from src.agents.plot import PlotAgent as PlotExpander

logger = logging.getLogger(__name__)

class WorldBibleGenerator:
    def __init__(self, repo, llm, pm, debate, marketing, auditor):
        self.repo = repo
        self.llm = llm
        self.pm = pm
        self.debate = debate
        self.marketing = marketing
        self.auditor = auditor

    def _generate_fallback_synopsis(
        self,
        bible_core: WorldBibleCore,
        genre: str,
        keywords: str,
        engine_key: str
    ) -> str:
        mc_name = (bible_core.mc_profile.name if bible_core.mc_profile else "") or "主人公"
        surface = (bible_core.mc_profile.surface_persona if bible_core.mc_profile else "") or "一見平凡な冒険者"
        conflict = (bible_core.mc_profile.inner_conflict if bible_core.mc_profile else "") or "生存への危機感と野望"
        constraint = (bible_core.mc_profile.iron_constraint if bible_core.mc_profile else "") or "絶対的なルールの遵守"

        arc_summaries = "\n".join([f"・章「{arc.title}」: {arc.summary}" for arc in bible_core.arcs]) if bible_core.arcs else ""

        details = DomainProfileService.get_fallback_synopsis_details(genre, keywords, engine_key)
        theme_desc = details["theme_desc"]
        ending_desc = details["ending_desc"]

        fallback_synopsis = (
            f"【作品タイトル】: {bible_core.title}\n\n"
            f"【コンセプト】: {bible_core.concept}\n\n"
            f"【主人公像】: 『{mc_name}』。表層の仮面（{surface}）と内なる葛藤（{conflict}）を抱え、"
            f"鉄則（{constraint}）を遵守しながら、{theme_desc}\n\n"
            f"【ストーリーアーク展開】:\n{arc_summaries}\n\n"
            f"{ending_desc}"
        )
        return fallback_synopsis

    async def create_hegemony_plan(
        self,
        genre: str = None,
        keywords: str = None,
        style_key: str = None,
        concept: str = None,
        title: str = "",
        cheat_scale: int = 4,
        growth_curve: str = "最初からカンスト(無双)",
        system_assist: int = 70,
        cost_severity: int = 2,
        target_eps: int = 10,
        initial_plot_limit: int = 3,
        config: PlanningConfig = None,
        reporter=None
    ) -> Tuple[int, WorldBible]:
        """
        覇権企画書の作成フロー全体を制御。UOWによるトランザクション管理下で実行。
        """
        from src.backend.database import UnitOfWork
        if config is None:
            from src.models.planning_config import PlanningConfig
            config = PlanningConfig(
                genre=genre,
                keywords=keywords,
                style_key=style_key,
                concept=concept,
                title=title,
                cheat_scale=cheat_scale,
                growth_curve=growth_curve,
                system_assist=system_assist,
                cost_severity=cost_severity,
                target_eps=target_eps,
                initial_plot_limit=initial_plot_limit,
                ultra_fast=True # Default to fast for this workflow
            )

        async with UnitOfWork(self.repo.db):
            if config.ultra_fast:
                book_id, bible_obj = await self._create_ultra_fast_plan(config, reporter)
            else:
                book_id, bible_obj = await self._create_standard_plan(config, reporter)
            return book_id, bible_obj

    async def _create_ultra_fast_plan(
        self,
        config: PlanningConfig,
        reporter
    ) -> Tuple[int, WorldBible]:
        if reporter:
            reporter.report("⚡ 超高速モード（統合プランニング）を起動しました...", "info")

        prompt = await self.pm.build_bible_creation_prompt(
            bible_core_schema=WorldBibleCore,
            world_rules_json="{}",
            genre=config.genre,
            keywords=config.keywords,
            concept=config.concept,
            target_eps=config.target_eps,
            book_id=None,
            title=config.title,
            style_key=config.style_key,
            engine_key=config.engine_key,
        )
        res = await self.llm.generate_json("gemini-2.0-flash", prompt, response_schema=UltraFastWorldBible, reporter=reporter)
        if not res.success:
            raise RuntimeError(f"超高速設定生成に失敗しました: {res.error_message}")

        uf_bible = UltraFastWorldBible.model_validate(res.metadata)
        bible_core = uf_bible.bible_core

        if config.title:
            bible_core.title = config.title
        else:
            config.title = bible_core.title

        bible_core.genre = config.genre
        bible_core.style_key = config.style_key
        bible_core.keywords = config.keywords
        bible_core.engine_key = config.engine_key
        bible_core.world_settings.tension_threshold = config.tension_threshold
        bible_core.world_settings.tension_gain = config.tension_gain

        if not bible_core.synopsis or len(bible_core.synopsis) < 50:
            bible_core.synopsis = self._generate_fallback_synopsis(bible_core, config.genre, config.keywords, config.engine_key)

        bible_dict = bible_core.model_dump()
        bible_dict["full_story_roadmap"] = [item.model_dump() for item in uf_bible.full_story_roadmap]
        bible_dict["engine_key"] = config.engine_key
        bible_dict["style_key"] = config.style_key

        bible_obj = safe_model_validate(WorldBible, bible_dict)
        book_id = await self.repo.create_book(
            title=config.title, genre=config.genre, concept=bible_obj.concept or config.keywords,
            synopsis=bible_obj.synopsis, target_eps=config.target_eps, style_dna={"mode": config.style_key},
            marketing_data=bible_obj.marketing_assets.model_dump() if bible_obj.marketing_assets else {}
        )
        await self.repo.save_full_world_bible(bible_obj, book_id=book_id)

        if config.initial_plot_limit > 0:
            ep_list = list(range(1, config.initial_plot_limit + 1))
            bible_json_str = json.dumps(bible_obj.model_dump(), ensure_ascii=False)
            sem = asyncio.Semaphore(2)

            async def _process_batch_item(ep_range):
                async with sem:
                    plot_prompt = await self.pm.build_ultra_fast_plot_batch_prompt(bible_json_str, ep_range, book_id=None)
                    plot_res = await self.llm.generate_json("gemini-2.0-flash", plot_prompt, response_schema=UltraFastPlotBatch, reporter=reporter)
                    if not plot_res.success:
                        raise RuntimeError(f"プロットバッチ生成に失敗しました: {plot_res.error_message}")
                    plots = UltraFastPlotBatch.model_validate(plot_res.metadata).plots
                    for p in plots:
                        await self.repo.save_plot(1, p.ep_num, p)

            async with asyncio.TaskGroup() as tg:
                tasks = [tg.create_task(_process_batch_item([ep])) for ep in ep_list]
            # Wait for all tasks to complete (TaskGroup does this automatically)

        return book_id, bible_obj

    async def _create_standard_plan(
        self,
        config: PlanningConfig,
        reporter
    ) -> Tuple[int, WorldBible]:
        if reporter:
            reporter.report("🌍 企画の深層検証を開始...", "info")

        # 1. ディベートとコンセプトの洗練
        title, concept, keywords, genre = await self._enrich_concept(
            config.title, config.concept, config.keywords, config.genre, config.run_debate
        )
        config.title = title
        config.concept = concept
        config.keywords = keywords
        config.genre = genre

        # 2. 世界法則の生成
        world_rules = await self._generate_world_rules(
            config.genre, config.keywords, config.engine_key, config.tension_threshold, config.tension_gain, reporter
        )

        # 3. キャラクター設定の生成
        mc_data, subs_data = await self._generate_characters(
            world_rules, config.genre, config.keywords, config.concept, config.style_key, config.engine_key, reporter
        )

        # 4. 企画書コア（WorldBibleCore）の生成
        bible_core = await self._generate_bible_core(
            world_rules, mc_data, subs_data, config.concept, config.genre, config.keywords, config.style_key, config.engine_key, config.target_eps, config.title, reporter
        )

        # 5. マーケティングパックの作成
        await self._apply_marketing_data(bible_core, config.engine_key)

        # 6. 整合性監査と自動修復
        await self._audit_and_repair(bible_core, reporter)

        # 7. マーケティングA/Bテスト
        await self._apply_marketing_ab_test(bible_core, config.genre, config.engine_key, config.title, reporter)

        # 8. ストーリーアークおよびロードマップの構築
        roadmap = await self._generate_roadmap(bible_core, config.target_eps, config.genre, config.engine_key, reporter)

        # 9. ロードマップを包含した最終的なWorldBibleオブジェクトの生成・保存
        if not bible_core.synopsis or len(bible_core.synopsis) < 50:
            bible_core.synopsis = self._generate_fallback_synopsis(bible_core, config.genre, config.keywords, config.engine_key)

        bible_obj = safe_model_validate(WorldBible, {**bible_core.model_dump(), "full_story_roadmap": roadmap, "engine_key": config.engine_key})
        book_id = await self.repo.save_full_world_bible(
            bible_obj, cheat_scale=config.cheat_scale, growth_curve=config.growth_curve,
            system_assist=config.system_assist, cost_severity=config.cost_severity, target_eps=config.target_eps
        )

        if config.initial_plot_limit > 0:
            # We will delegate back or use PlotExpander
            expander = PlotExpander(self.repo, self.llm, self.pm, self.auditor, self._generate_fallback_synopsis)
            await expander.expand_plots(book_id, list(range(1, config.initial_plot_limit + 1)), bible_obj.arcs, reporter=reporter)

        return book_id, bible_obj

    async def _enrich_concept(self, title: str, concept: str, keywords: str, genre: str, run_debate: bool) -> Tuple[str, str, str, str]:
        if run_debate and self.debate:
            current_concept = {"title": title, "genre": genre, "keywords": keywords, "concept": concept}
            debate_res = await self.debate.run_debate(current_concept)
            refined = debate_res["final_concept"]
            return (
                refined.get("title", title),
                refined.get("concept", concept),
                refined.get("keywords", keywords),
                refined.get("genre", genre)
            )
        return title, concept, keywords, genre

    async def _generate_world_rules(self, genre: str, keywords: str, engine_key: str, tension_threshold: int, tension_gain: float, reporter) -> WorldRules:
        prompt = await self.pm.build_world_creation_prompt(genre, keywords, WorldRules, engine_key=engine_key, book_id=None)
        world_res = await self.llm.generate_json(MODEL_PLANNING, prompt, response_schema=WorldRules, temp=0.8, reporter=reporter)
        world_rules = WorldRules.model_validate(world_res.metadata) if world_res.success else WorldRules()
        world_rules.tension_threshold = tension_threshold
        world_rules.tension_gain = tension_gain
        # causality_map が空の場合、ジャンル・エンジン依存のデフォルトを設定
        if not world_rules.causality_map:
            logger.warning("causality_map が LLM から返されませんでした。ジャンル別デフォルトを設定します。")
            world_rules.causality_map = DomainProfileService.get_default_causality_map(genre, engine_key)
        return world_rules

    async def _generate_characters(self, world_rules: WorldRules, genre: str, keywords: str, concept: str, style_key: str, engine_key: str, reporter) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        # Memory retrieval could be mocked or passed
        mc_prompt = await self.pm.build_mc_creation_prompt(world_rules.model_dump_json(), genre, keywords, concept, style_key=style_key, engine_key=engine_key, book_id=None)
        mc_res = await self.llm.generate_json(MODEL_PLANNING, mc_prompt, temp=0.8, reporter=reporter)
        mc_data = mc_res.metadata or {}

        sub_prompt = await self.pm.build_sub_char_creation_prompt(world_rules.model_dump_json(), json.dumps(mc_data, ensure_ascii=False), world_rules.causality_map, safe_get(mc_data, "name", ""), genre=genre, keywords=keywords, book_id=None)
        sub_res = await self.llm.generate_json(MODEL_PLANNING, sub_prompt, temp=0.8, reporter=reporter)
        subs_data = safe_get(sub_res.metadata, "characters", []) if sub_res.success else []

        return mc_data, subs_data

    async def _generate_bible_core(self, world_rules: WorldRules, mc_data: Dict[str, Any], subs_data: List[Dict[str, Any]], concept: str, genre: str, keywords: str, style_key: str, engine_key: str, target_eps: int, title: str, reporter) -> WorldBibleCore:
        bible_prompt = await self.pm.build_bible_creation_prompt(WorldBibleCore, world_rules.model_dump_json(), concept or genre + 'の覇権作品', target_eps, genre=genre, style_key=style_key, engine_key=engine_key, book_id=None)
        bible_res = await self.llm.generate_json(MODEL_PLANNING, bible_prompt, response_schema=WorldBibleCore, reporter=reporter)
        bible_core = WorldBibleCore.model_validate(bible_res.metadata)

        bible_core.world_settings = world_rules
        bible_core.mc_profile = CharacterRegistry.model_validate(mc_data) if mc_data else CharacterRegistry()
        bible_core.sub_characters = [CharacterRegistry.model_validate(s) for s in subs_data[:5]]

        if engine_key == "enigma":
            world_rules.truth_ledger = {
                "core_mystery": {
                    "truth": safe_get(mc_data, "core_mystery", "未解明の謎の真実"),
                    "public_facade": "大衆が信じている偽りの歴史",
                    "discovery_difficulty": "極大"
                },
                "antagonist_blind_spots": ["主人公の真の能力への過小評価", "側近の裏切り", "主人公が握っている決定的な弱点"],
                "foreshadowing_budget": {"unresolved_count": 0, "planned_payoffs": []}
            }
            bible_core.story_direction += "\n\n【Enigmaモード：知能戦絶対指令】\n1. [情報の非対称性]: 常に『誰が何を知っているか』を意識せよ。\n2. [戦略的優位]: 主人公の行動は常に3手先を読んだ布石として描け。\n3. [論理的カタルシス]: 驚きは『意外性』ではなく『納得感』から生み出せ。"

        bible_core.title = title or bible_core.title
        bible_core.concept = concept or bible_core.concept or f"「{keywords}」をテーマに「{genre}」の常識を覆し、読者のカタルシスを最大化する覇権小説"
        bible_core.engine_key = engine_key
        return bible_core

    async def _apply_marketing_data(self, bible_core: WorldBibleCore, engine_key: str) -> None:
        if self.marketing:
            mkt_audit = await self.marketing.generate_marketing_pack(bible_core.title, bible_core.synopsis, 0, engine_key=engine_key)
            if mkt_audit:
                bible_core.marketing_assets.catchcopies = mkt_audit.get("catchcopies", [])
                bible_core.marketing_assets.tags = list(set(bible_core.marketing_assets.tags + mkt_audit.get("tags", [])))

    async def _audit_and_repair(self, bible_core: WorldBibleCore, reporter) -> None:
        if self.auditor:
            audit_res = await self.auditor.audit_plot_integrity(1, bible_core.synopsis, bible_core.world_settings.model_dump_json(), reporter=reporter)
            if not audit_res.is_consistent:
                repair_prompt = await self.pm.build_global_repair_prompt(
                    conflict_report=audit_res.conflict_report,
                    synopsis=bible_core.synopsis,
                    world_rules=bible_core.world_settings.model_dump_json(),
                    mc_profile=bible_core.mc_profile.model_dump_json() if bible_core.mc_profile else "{}"
                )
                repair_res = await self.llm.generate_json(MODEL_PLANNING, repair_prompt, response_schema=GlobalLogicRepairResult, reporter=reporter)
                if repair_res.success:
                    repair_data = GlobalLogicRepairResult.model_validate(repair_res.metadata)
                    bible_core.synopsis = repair_data.synopsis
                    if repair_data.world_rules:
                        bible_core.world_settings = bible_core.world_settings.model_copy(update=repair_data.world_rules)
                    if repair_data.mc_profile and bible_core.mc_profile:
                        bible_core.mc_profile = bible_core.mc_profile.model_copy(update=repair_data.mc_profile)

    async def _apply_marketing_ab_test(self, bible_core: WorldBibleCore, genre: str, engine_key: str, title: str, reporter) -> None:
        prompt = await self.pm.build_marketing_ab_test_prompt(bible_core.concept, genre=genre, engine_key=engine_key)
        mkt_res = await self.llm.generate_json(MODEL_PLANNING, prompt, reporter=reporter)
        if mkt_res.success and safe_get(mkt_res.metadata, "ab_test_candidates") is not None:
            candidates = safe_get(mkt_res.metadata, "ab_test_candidates")
            winning_index = safe_get(mkt_res.metadata, "winning_index", 0)
            win = candidates[winning_index]
            if not title: bible_core.title = safe_get(win, "title", bible_core.title)
            bible_core.marketing_assets.tags = safe_get(win, "tags", [])

    async def _generate_roadmap(self, bible_core: WorldBibleCore, target_eps: int, genre: str, engine_key: str, reporter) -> List[Any]:
        if not bible_core.arcs:
            if target_eps <= 5:
                bible_core.arcs = [ArcBlueprint(arc_num=1, start_ep=1, end_ep=target_eps, title="メインエピソード", summary=bible_core.synopsis[:100])]
            else:
                arc_prompt = self.pm.build_arc_generation_prompt(bible_core.title, bible_core.synopsis, target_eps, genre=genre, engine_key=engine_key)
                arc_res = await self.llm.generate_json(MODEL_PLANNING, arc_prompt, response_schema=ArcList, reporter=reporter)
                bible_core.arcs = safe_get(arc_res.metadata, "arcs", []) if arc_res.success else []

        roadmap = []
        rm_prompt = None
        if bible_core.arcs:
            rm_prompt = await self.pm.build_roadmap_prompt(bible_core.title, bible_core.synopsis, target_eps, RoadmapList, genre=genre, engine_key=engine_key, start_ep=safe_get(bible_core.arcs[0], "start_ep"), end_ep=safe_get(bible_core.arcs[0], "end_ep"))
            rm_res = await self.llm.generate_json(MODEL_PLANNING, rm_prompt, response_schema=RoadmapList, reporter=reporter)
            if rm_res.success:
                roadmap = safe_get(rm_res.metadata, "full_story_roadmap", [])

        # [Q2] ロードマップが空の場合: 1回だけ再生成を試みる
        if not roadmap and rm_prompt:
            logger.warning("ロードマップ生成が失敗しました。1回再試行します...")
            if reporter:
                reporter.report("⚠️ ロードマップ生成に失敗。再試行中...", "warning")
            rm_res_retry = await self.llm.generate_json(
                MODEL_PLANNING, rm_prompt, response_schema=RoadmapList, reporter=reporter
            )
            if rm_res_retry.success:
                roadmap = safe_get(rm_res_retry.metadata, "full_story_roadmap", [])

        # 再試行後もなお空の場合: プレースホルダーフォールバック（致命的停止を防止）
        if not roadmap:
            logger.warning("ロードマップ再生成も失敗。プレースホルダーフォールバックを生成します。")
            if reporter:
                reporter.report("⚠️ ロードマップを自動生成できませんでした。プレースホルダーで続行します。", "warning")
            roadmap = [
                {
                    "ep_num": i,
                    "title": f"第{i}話",
                    "one_line_summary": f"物語の第{i}幕（プロット展開時に詳細化）",
                    "tension_level": 50,
                    "resolution_style": "Cheat",
                    "antagonist_status": "現状維持"
                }
                for i in range(1, target_eps + 1)
            ]
        return roadmap
