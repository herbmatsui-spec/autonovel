import json
import logging
import time
import datetime
import asyncio
import io
import zipfile
import random
import re
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple
from config import (
    STYLE_DEFINITIONS, STYLE_REFINEMENT_DIRECTIONS, MODEL_PLOT_EXPANSION, 
    MODEL_WRITING, MODEL_PLANNING, FORBIDDEN_WORD_REPLACEMENTS,
    STRESS_CLIMAX_BONUS, STRESS_CATHARSIS_THRESHOLD, STRESS_FILLER_THRESHOLD,
    STRESS_HATE_GAIN_BASE, CHEAT_DESCRIPTIONS, ROUTINE_VARIATIONS,
    NARRATIVE_PROPS, DAILY_MICRO_HOOKS, TRAGEDY_VARIATIONS,
    DEFAULT_GOLDEN_PEAKS
)
from models import (
    LogicalAuditResult, ForeshadowingAudit, WorldState, StyleDNA, 
    WorldRules, CharacterRegistry, WorldBibleCore, RoadmapList, WorldBible,
    EpisodeDraft, HegemonyAuditResult, PlotDbModel, PlotEpisode
)
from sanitizer import AtmosphereGenerator, ContentValidator, TonePerfector, OutputSanitizer
from engine_utils import verify_character_tone, is_light_style, safe_model_validate
from engine_style_rag import StyleRagManager

if TYPE_CHECKING:
    from engine import UltimateHegemonyEngine

logger = logging.getLogger(__name__)

# ==========================================
# BaseAgent (蜈ｱ騾壹う繝ｳ繧ｿ繝ｼ繝輔ぉ繝ｼ繧ｹ)
# ==========================================
class BaseAgent:
    """蜈ｨ繧ｨ繝ｼ繧ｸ繧ｧ繝ｳ繝医・蝓ｺ蠎輔け繝ｩ繧ｹ"""
    def __init__(self, engine: "UltimateHegemonyEngine"):
        self.engine = engine

class LogicalAuditor(BaseAgent):
    """迚ｩ隱槭・謨ｴ蜷域ｧ縺ｨ莨冗ｷ壼屓蜿弱・逶｣譟ｻ繧呈球蠖・""

    async def audit_plot(self, book_id: int, ep_num: int, plot_bp: str, script: str) -> LogicalAuditResult:
        # 謾ｹ蝟・｡・: 螻･豁ｴ蜿門ｾ励ｒ ContextManager 縺ｫ荳蜈・喧
        past_facts = await self.engine.ctx_mgr.build_past_context(book_id, ep_num)
        prompt = self.engine.pm.build_logical_audit_prompt(past_facts, plot_bp, script)
        res = await self.engine._generate_json(MODEL_PLOT_EXPANSION, prompt, response_schema=LogicalAuditResult)
        if res.success: return LogicalAuditResult.model_validate(res.metadata)
        return LogicalAuditResult(is_consistent=True)

    async def audit_foreshadowing_payoff(self, book_id: int, ep_num: int, content: str) -> ForeshadowingAudit:
        bible = await self.engine.repo.get_latest_bible(book_id)
        if not bible:
            return ForeshadowingAudit(is_recovered=True)
        settings = bible.settings if isinstance(bible.settings, dict) else json.loads(bible.settings or "{}") # type: ignore
        f_map = settings.get("foreshadowing_map", []) # type: ignore
        prompt = self.engine.pm.build_foreshadowing_audit_prompt(f_map, content)
        res = await self.engine._generate_json(MODEL_PLOT_EXPANSION, prompt, response_schema=ForeshadowingAudit)
        if res.success: return ForeshadowingAudit.model_validate(res.metadata)
        return ForeshadowingAudit(is_recovered=True)

    async def lightweight_audit_world_state(self, current: WorldState, previous: Optional[WorldState]) -> LogicalAuditResult:
        """邁｡譏鍋噪縺ｪ迥ｶ諷狗泝逶ｾ繝√ぉ繝・け"""
        if not previous: return LogicalAuditResult(is_consistent=True)
        conflicts = []
        for char, state in current.character_states.items():
            prev_state = previous.character_states.get(char, "")
            if "豁ｻ莠｡" in prev_state and "逕溷ｭ・ in state:
                conflicts.append(f"遏帷崟讀懃衍: {char} 縺悟燕隧ｱ縺ｧ豁ｻ莠｡縺励※縺・∪縺吶′縲∽ｻ願ｩｱ縺ｧ逕溷ｭ倡憾諷九↓縺ｪ縺｣縺ｦ縺・∪縺吶・)
        if conflicts: return LogicalAuditResult(is_consistent=False, conflict_points=conflicts, severity="Major")
        return LogicalAuditResult(is_consistent=True)

class InternalLogicValidator(BaseAgent):
    """
    縲主鋸驕輔＞縲上・繝ｭ繧ｻ繧ｹ縺ｮ隲也炊逧・紛蜷域ｧ繧貞宍蟇・↓讀懆ｨｼ縺吶ｋ縲・    莠句ｮ・A) -> 邨ｶ譛・B) -> 隱､隱・C) -> 隕夐・(D) 縺ｮ4繧ｹ繝・ャ繝励ｒ讀懆ｨｼ縲・    """
    async def validate_misunderstanding_flow(self, content: str, gap_desc: str) -> Tuple[bool, List[str]]:
        prompt = (
            self.engine.pm.build_misunderstanding_validation_prompt(content, gap_desc)
        )
        res = await self.engine._generate_json(MODEL_PLANNING, prompt, temp=0.2)
        meta = res.metadata if res.success else {}
        return meta.get("passed", True), meta.get("missing_steps", [])

class PlotIntegrityMonitor(BaseAgent):
    """
    險ｭ險亥峙・・lueprint・峨→譛ｬ譁・・迚ｩ逅・噪荳閾ｴ繧堤屮隕悶・    驥崎ｦ√い繧､繝・Β縲・浹縲∝虚菴懊・蜃ｺ迴ｾ邇・′80%譛ｪ貅縺ｪ繧牙・逕滓・繧偵ヨ繝ｪ繧ｬ繝ｼ縲・    """
    def extract_keywords(self, blueprint: str) -> List[str]:
        """險ｭ險亥峙縺九ｉ驥崎ｦ√く繝ｼ繝ｯ繝ｼ繝峨ｒ謚ｽ蜃ｺ縺吶ｋ・医く繝｣繝・す繝･逕ｨ・・""
        if not blueprint: return []
        # 縲後阪ｄ縲弱上〒蝗ｲ縺ｾ繧後◆蜊倩ｪ槭√♀繧医・2譁・ｭ嶺ｻ･荳翫・貍｢蟄励・繧ｫ繧ｿ繧ｫ繝翫ｒ謚ｽ蜃ｺ
        keywords = re.findall(r'縲・.*?)縲鋼縲・.*?)縲・, blueprint)
        keywords = [k[0] or k[1] for k in keywords if k[0] or k[1]]
        # 陬懷勧逧・↓2譁・ｭ嶺ｻ･荳翫・貍｢蟄励・繧ｫ繧ｿ繧ｫ繝翫ｂ霑ｽ蜉
        ja_keywords = re.findall(r'[荳-鮴縲・{2,}|[繧｡-繝ｶ繝ｼ]{2,}', blueprint)
        keywords.extend(ja_keywords)
        # 驥崎､・賜髯､縺ｨ繧ｯ繝ｪ繝ｼ繝九Φ繧ｰ
        return list(set([k.strip() for k in keywords if k.strip()]))[:15]

    async def check_integrity(self, keywords: List[str], blueprint: str, content: str) -> Tuple[bool, float, List[str]]:
        """迚ｩ逅・噪縺ｪ荳閾ｴ遒ｺ隱・""
        if not keywords: return True, 1.0, []

        # 2. 譛ｬ譁・・縺ｧ縺ｮ蜃ｺ迴ｾ繝√ぉ繝・け
        found = []
        missing = []
        for kw in keywords:
            if kw in content:
                found.append(kw)
            else:
                missing.append(kw)
        
        hit_rate = len(found) / len(keywords)
        is_ok = hit_rate >= 0.8
        
        # 驥崎ｦ√い繧､繝・Β・郁ｨｭ險亥峙縺ｧ蠑ｷ隱ｿ縺輔ｌ縺ｦ縺・ｋ繧ゅ・・峨・豸亥､ｱ繝√ぉ繝・け
        critical_missing = [m for m in missing if f"驥崎ｦ・{m}" in blueprint or f"蠢・・{m}" in blueprint]
        if critical_missing: is_ok = False

        return is_ok, hit_rate, missing

class MarketingAgent:
    """螳｣莨昴ヱ繝・け縲√ち繧､繝医Ν縲∵枚菴泥NA縺ｮ蛻・梵縺ｨ逕滓・繧呈球蠖・""
    def __init__(self, engine: "UltimateHegemonyEngine"):
        self.engine = engine

    async def generate_marketing_pack(self, book_title: str, synopsis: str, latest_ep: int) -> Optional[Dict[str, Any]]:
        prompt = self.engine.pm.build_marketing_pack_prompt(book_title, synopsis, latest_ep)
        res = await self.engine._generate_json(MODEL_PLANNING, prompt)
        return res.metadata if res.success else None

    async def generate_titles(self, genre: str, keywords: str) -> List[str]:
        prompt = self.engine.pm.build_title_generation_prompt(genre, keywords)
        res = await self.engine._generate_json(MODEL_PLANNING, prompt)
        if res.success and isinstance(res.metadata, dict) and "titles" in res.metadata:
            return res.metadata["titles"]
        return ["隕・ｨｩ縺ｮ蟋九∪繧・, "霑ｽ謾ｾ縺輔ｌ縺滓怙蠑ｷ閠・, "蜈ｨ縺ｦ繧定ｶ・∴縺苓・]

    async def analyze_style_dna(self, sample_text: str) -> Dict[str, Any]:
        prompt = self.engine.pm.build_style_dna_analysis_prompt(sample_text)
        res = await self.engine._generate_json(MODEL_PLANNING, prompt, temp=0.3, response_schema=StyleDNA)
        return res.metadata if res.success else {"name": "蛻・梵螟ｱ謨・, "instruction": "", "score": 0, "analysis": ""}

    async def create_export_package(self, book_id: int) -> Tuple[bytes, str]:
        """菴懷刀繝・・繧ｿ荳蠑擾ｼ域悽譁・∬ｨｭ螳壹√・繝ｭ繝・ヨ縲゛SON繝繝ｳ繝暦ｼ峨ｒZIP繝代ャ繧ｱ繝ｼ繧ｸ蛹悶☆繧・""
        book = await self.engine.repo.get_book(book_id)
        if not book: raise ValueError("菴懷刀縺瑚ｦ九▽縺九ｊ縺ｾ縺帙ｓ縲・)

        chapters = await self.engine.repo.get_all_non_anchor_chapters(book_id, order_by="ep_num")
        chars    = await self.engine.repo.get_all_characters(book_id)
        bible    = await self.engine.repo.get_latest_bible(book_id)
        plots    = await self.engine.repo.get_all_plots(book_id)

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            # 01: 譛ｬ譁・            full_text = "".join(f"隨ｬ{c.ep_num}隧ｱ {c.title}\n\n{c.content}\n\n" for c in chapters)
            z.writestr("01_譛ｬ譁・txt", full_text)

            # 02: 繧ｭ繝｣繝ｩ繧ｯ繧ｿ繝ｼ繝ｻ荳也阜隕ｳ險ｭ螳・            settings_str = ""
            if bible and bible.settings:
                settings_str = json.dumps(bible.settings, ensure_ascii=False, indent=2) if isinstance(bible.settings, dict) else str(bible.settings)
            
            setting_text = f"縲蝉ｸ也阜隕ｳ險ｭ螳壹曾n{settings_str}\n\n"
            setting_text += "縲舌く繝｣繝ｩ繧ｯ繧ｿ繝ｼ險ｭ螳壹曾n"
            for c in chars:
                try:
                    if hasattr(c, "registry_data"):
                        reg = c.registry_data or {}
                        if isinstance(reg, str):
                            try: reg = json.loads(reg)
                            except: reg = {}
                    elif hasattr(c, "model_dump"):
                        reg = c.model_dump()
                    else:
                        reg = {}
                except Exception:
                    reg = {}
                setting_text += f"笆 {c.name} ({c.role})\n諤ｧ譬ｼ: {reg.get('personality', '')}\n閭ｽ蜉・ {reg.get('ability', '')}\n\n"
            z.writestr("02_繧ｭ繝｣繝ｩ繧ｯ繧ｿ繝ｼ繝ｻ荳也阜隕ｳ險ｭ螳夐寔.txt", setting_text)

            # 03: 菴懷刀逋ｻ骭ｲ逕ｨ繝・・繧ｿ
            mkt = book.marketing_data if isinstance(book.marketing_data, dict) else {}
            reg_text = (
                f"縲舌ち繧､繝医Ν縲曾n{book.title}\n\n"
                f"縲舌≠繧峨☆縺倥曾n{book.synopsis or ''}\n\n"
                f"縲舌く繝｣繝・メ繧ｳ繝斐・縲曾n{', '.join(mkt.get('catchcopies', [])) if mkt.get('catchcopies') else ''}\n\n"
                f"縲舌ち繧ｰ縲曾n{', '.join(mkt.get('tags', [])) if mkt.get('tags') else ''}\n"
            )
            z.writestr("03_菴懷刀逋ｻ骭ｲ逕ｨ繝・・繧ｿ.txt", reg_text)

            # 04: 蜈ｨ隧ｱ繝励Ο繝・ヨ讒区・譯・            plot_text = "縲仙・隧ｱ繝励Ο繝・ヨ讒区・譯医曾n\n"
            for p in plots:
                plot_text += f"隨ｬ{p.ep_num}隧ｱ・嘴p.title}\n"
                if p.summary: plot_text += f"  荳陦後≠繧峨☆縺假ｼ嘴p.summary}\n"
                plot_text += f"縲占ｨｭ險亥峙縲曾n{p.detailed_blueprint}\n"
                if p.next_hook:
                    hook_desc = p.next_hook
                    if isinstance(p.next_hook, dict): hook_desc = p.next_hook.get('description', '')
                    plot_text += f"縲先ｬ｡蝗槭∈縺ｮ蠑輔″縲曾n{hook_desc}\n"
                plot_text += "\n" + "-"*30 + "\n\n"
            z.writestr("04_蜈ｨ隧ｱ繝励Ο繝・ヨ讒区・譯・txt", plot_text)

            # 05: JSON繝繝ｳ繝・            dump_data = {
                "book": book.model_dump(),
                "bible": bible.model_dump() if bible else {},
                "plots": [p.model_dump() for p in plots],
                "chapters": [c.model_dump() for c in chapters],
            }
            z.writestr("05_菴懷刀繝・・繧ｿ繝繝ｳ繝・json", json.dumps(dump_data, ensure_ascii=False, indent=2))

        return buf.getvalue(), f"{book.title}_隕・ｨｩ菴懷刀.zip"

class PlanningAgent:
    """隕・ｨｩ莨∫判縺ｮ遶区｡医→蜀肴ｧ狗ｯ峨ｒ諡・ｽ・""
    def __init__(self, engine: "UltimateHegemonyEngine"):
        self.engine = engine

    async def create_hegemony_plan(
        self, genre: str, keywords: str, style_key: str, concept: str, title: str,
        cheat_scale: int, growth_curve: str, system_assist: int, cost_severity: int,
        target_eps: int, initial_plot_limit: int, reporter=None,
    ) -> Tuple[int, WorldBible]:
        if reporter:
            reporter.report("訣 荳也阜隕ｳ縺ｮ豺ｱ螻､逕滓・繧帝幕蟋・..", "info")

        world_prompt = self.engine.pm.build_world_creation_prompt(genre, keywords, WorldRules)

        world_res = await self.engine._generate_json(MODEL_PLANNING, world_prompt, response_schema=WorldRules, temp=0.8)
        if not world_res.success:
            logger.warning(f"荳也阜隕ｳ險ｭ螳壹・逕滓・縺ｫ螟ｱ謨励＠縺ｾ縺励◆縲ゅョ繝輔か繝ｫ繝郁ｨｭ螳壹ｒ菴ｿ逕ｨ縺励∪縺・ {world_res.error_message}")
            world_rules = WorldRules()
        else:
            world_rules = WorldRules.model_validate(world_res.metadata)

        if reporter:
            reporter.report("ｦｸ 荳ｻ莠ｺ蜈ｬ・・C・峨ｒ蛟句挨騾蠖｢荳ｭ...", "info")
            
        mc_prompt = self.engine.pm.build_mc_creation_prompt(
            world_rules.model_dump_json(), genre, keywords, concept
        )

        mc_res = await self.engine._generate_json(MODEL_PLANNING, mc_prompt, temp=0.8)
        if not mc_res.success:
            logger.warning(f"荳ｻ莠ｺ蜈ｬ縺ｮ逕滓・縺ｫ螟ｱ謨励＠縺ｾ縺励◆: {mc_res.error_message}")
        mc_data = mc_res.metadata or {}
        # MC縺ｮ蜷榊燕繧偵し繝悶く繝｣繝ｩ逕滓・繝励Ο繝ｳ繝励ヨ縺ｫ貂｡縺吶◆繧√↓謚ｽ蜃ｺ
        mc_name = mc_data.get("name", "")

        if reporter:
            reporter.report("則 繧ｵ繝悶く繝｣繝ｩ繧ｯ繧ｿ繝ｼ鄒､繧剃ｸ諡ｬ蜿ｬ蝟壻ｸｭ...", "info")

        # 謾ｹ蝟・ 荳也阜隕ｳ縺ｮ蝗譫懷ｾ・causality_map)繧堤峩謗･豕ｨ蜈･縺励∽ｸ也阜縺ｨ蟇・磁縺ｫ髢｢繧上ｋ繧ｭ繝｣繝ｩ繧堤函謌・        sub_prompt = self.engine.pm.build_sub_char_creation_prompt(
            world_rules.model_dump_json(), json.dumps(mc_data, ensure_ascii=False), world_rules.causality_map,
            mc_name
        )
        sub_res = await self.engine._generate_json(MODEL_PLANNING, sub_prompt, temp=0.8)
        if not sub_res.success:
            logger.warning(f"繧ｵ繝悶く繝｣繝ｩ繧ｯ繧ｿ繝ｼ縺ｮ逕滓・縺ｫ螟ｱ謨励＠縺ｾ縺励◆: {sub_res.error_message}")
        subs_data = sub_res.metadata.get("characters", [])

        if reporter:
            reporter.report("搭 莨∫判譖ｸ繧堤ｵｱ蜷井ｸｭ...", "info")
        bible_prompt = self.engine.pm.build_bible_creation_prompt(WorldBibleCore, world_rules.model_dump_json(), concept or genre + '縺ｮ隕・ｨｩ菴懷刀', target_eps)
        bible_res  = await self.engine._generate_json(MODEL_PLANNING, bible_prompt, response_schema=WorldBibleCore)
        if not bible_res.success:
            raise RuntimeError(f"繧ｳ繧｢險ｭ螳夂函謌仙､ｱ謨・ {bible_res.error_message}")
        bible_core = WorldBibleCore.model_validate(bible_res.metadata)
        bible_core.world_settings = world_rules
        if mc_data:
            try:
                normalized_mc = OutputSanitizer.normalize_metadata(mc_data)
                bible_core.mc_profile = CharacterRegistry.model_validate(normalized_mc)
            except Exception:
                logger.error("MC繝励Ο繝輔ぅ繝ｼ繝ｫ縺ｮ繝舌Μ繝・・繧ｷ繝ｧ繝ｳ縺ｫ螟ｱ謨励＠縺ｾ縺励◆・医ョ繝ｼ繧ｿ讒矩荳堺ｸ閾ｴ・・)
        if subs_data:
            try:
                bible_core.sub_characters = [CharacterRegistry.model_validate(OutputSanitizer.normalize_metadata(s)) for s in subs_data[:5]]
            except Exception:
                logger.error("繧ｵ繝悶く繝｣繝ｩ繧ｯ繧ｿ繝ｼ縺ｮ繝舌Μ繝・・繧ｷ繝ｧ繝ｳ縺ｫ螟ｱ謨励＠縺ｾ縺励◆・医ョ繝ｼ繧ｿ讒矩荳堺ｸ閾ｴ・・)
        if title:
            bible_core.title = title

        if reporter:
            reporter.report("投 繧ｿ繧､繝医Ν繝ｻ繧ｿ繧ｰ縺ｮAB繝・せ繝井ｸｭ...", "info")
        mkt_prompt = self.engine.pm.build_marketing_ab_test_prompt(bible_core.concept)
        mkt_res = await self.engine._generate_json(MODEL_PLANNING, mkt_prompt)
        if mkt_res.success and "ab_test_candidates" in mkt_res.metadata:
            win = mkt_res.metadata["ab_test_candidates"][mkt_res.metadata.get("winning_index", 0)]
            bible_core.title                           = win.get("title", bible_core.title)
            bible_core.marketing_assets.tags           = win.get("tags", [])
            bible_core.marketing_assets.ab_test_candidates = mkt_res.metadata["ab_test_candidates"]
            if reporter:
                reporter.report(f"醇 譛蠑ｷ繧ｿ繧､繝医Ν豎ｺ螳・ 縲施bible_core.title}縲・, "info")

        if reporter:
            reporter.report("亮・・蜈ｨ隧ｱ繝ｭ繝ｼ繝峨・繝・・繧呈ｧ狗ｯ我ｸｭ...", "info")
        rm_prompt = self.engine.pm.build_roadmap_prompt(bible_core.title, bible_core.synopsis, target_eps, RoadmapList)
        rm_res    = await self.engine._generate_json(MODEL_PLANNING, rm_prompt, response_schema=RoadmapList)
        roadmap   = rm_res.metadata.get("full_story_roadmap", []) if rm_res.success else []

        bible_dict               = bible_core.model_dump()
        bible_dict["full_story_roadmap"] = roadmap
        bible_obj = safe_model_validate(WorldBible, bible_dict)

        book_id = await self.engine.repo.save_full_world_bible(
            bible_obj, cheat_scale=cheat_scale, growth_curve=growth_curve,
            system_assist=system_assist, cost_severity=cost_severity, target_eps=target_eps
        )

        if reporter:
            reporter.report(f"笨・莨∫判菫晏ｭ伜ｮ御ｺ・(ID: {book_id})縲ょ濤遲・ヱ繧､繝励Λ繧､繝ｳ繧呈ｺ門ｙ荳ｭ...", "info")

        # initial_plot_limit縺梧欠螳壹＆繧後※縺・ｋ蝣ｴ蜷医・縺ｿ螻暮幕・医°繧薙◆繧薙Δ繝ｼ繝峨〒縺ｯ0繧呈欠螳壹＠縺ｦ繝代う繝励Λ繧､繝ｳ縺ｸ豬√☆・・        if initial_plot_limit > 0:
            await self.expand_plots(
                book_id, list(range(1, initial_plot_limit + 1)), bible_obj.arcs, reporter=reporter
            )
        return book_id, bible_obj

    async def audit_bible_completeness(self, bible: WorldBible, reporter=None) -> bool:
        """
        隧ｳ邏ｰ繝励Ο繝・ヨ螻暮幕蜑阪↓縲∽ｼ∫判譖ｸ・・ible・峨・驥崎ｦ・・岼縺ｫ謚懊￠貍上ｌ縺後↑縺・°繝√ぉ繝・け縺吶ｋ縲・        荳榊ｙ縺後≠繧句ｴ蜷医・隴ｦ蜻翫ｒ蜃ｺ縺励∬・蜻ｽ逧・↑蝣ｴ蜷医・ False 繧定ｿ斐☆縲・        """
        if reporter:
            reporter.report("剥 莨∫判譖ｸ縺ｮ謨ｴ蜷域ｧ繝ｻ螳悟ｙ諤ｧ繧呈怙邨ゅメ繧ｧ繝・け荳ｭ...", "info")
        
        issues = []
        
        # 1. 蝓ｺ譛ｬ諠・ｱ縺ｮ繝√ぉ繝・け
        if not bible.title or "辟｡鬘・ in bible.title: issues.append("菴懷刀繧ｿ繧､繝医Ν縺梧悴險ｭ螳壹〒縺吶・)
        if len(bible.synopsis) < 200: issues.append("蜈ｨ菴薙≠繧峨☆縺倥・譖ｸ縺崎ｾｼ縺ｿ縺御ｸ崎ｶｳ縺励※縺・∪縺吶・)
        
        # 2. 繧ｭ繝｣繝ｩ繧ｯ繧ｿ繝ｼ縺ｮ繝√ぉ繝・け
        mc = bible.mc_profile
        if not mc.name: issues.append("荳ｻ莠ｺ蜈ｬ縺ｮ蜷榊燕縺瑚ｨｭ螳壹＆繧後※縺・∪縺帙ｓ縲・)
        
        # registry_data 縺ｮ讒矩繧呈ｨ｡縺励◆繝√ぉ繝・け・・haracterRegistry繧ｪ繝悶ず繧ｧ繧ｯ繝医→縺励※隧穂ｾ｡・・        if not mc.expansion_hooks:
            issues.append(f"荳ｻ莠ｺ蜈ｬ {mc.name} 縺ｮ縲取緒蜀吶ヵ繝・け(Expansion Hooks)縲上′遨ｺ縺ｧ縺吶ょ濤遲・・雉ｪ縺御ｽ惹ｸ九☆繧区＄繧後′縺ゅｊ縺ｾ縺吶・)
        if not mc.first_person: issues.append(f"荳ｻ莠ｺ蜈ｬ {mc.name} 縺ｮ荳莠ｺ遘ｰ縺梧悴險ｭ螳壹〒縺吶・)

        # 3. 荳也阜隕ｳ繝ｻ繝ｭ繝ｼ繝峨・繝・・縺ｮ繝√ぉ繝・け
        if not bible.world_settings.causality_map:
            issues.append("荳也阜縺ｮ蝗譫懷ｾ具ｼ・ausality Map・峨′遨ｺ縺ｧ縺吶ょｱ暮幕縺後＃驛ｽ蜷井ｸｻ鄒ｩ縺ｫ縺ｪ繧九Μ繧ｹ繧ｯ縺後≠繧翫∪縺吶・)
        
        roadmap_len = len(bible.full_story_roadmap)
        if roadmap_len == 0:
            issues.append("蜈ｨ隧ｱ繝ｭ繝ｼ繝峨・繝・・縺檎函謌舌＆繧後※縺・∪縺帙ｓ縲りｩｳ邏ｰ繝励Ο繝・ヨ縺ｸ騾ｲ繧√∪縺帙ｓ縲・)

        if not issues:
            if reporter: reporter.report("笨ｨ 莨∫判譖ｸ縺ｮ蛛･蜈ｨ諤ｧ繝√ぉ繝・け蜷域ｼ縲ゅ・繝ｭ繝・ヨ隧ｳ邏ｰ蛹悶∈遘ｻ陦後＠縺ｾ縺吶・, "info")
            return True
        else:
            for issue in issues:
                logger.warning(f"[Bible Audit] {issue}")
                if reporter: reporter.report(issue, "warning")
            
            # 閾ｴ蜻ｽ逧・↑谺關ｽ・医Ο繝ｼ繝峨・繝・・縺ｪ縺暦ｼ峨′縺ゅｋ蝣ｴ蜷医・縺ｿ荳ｭ譁ｭ
            if roadmap_len == 0:
                if reporter: reporter.report("圷 閾ｴ蜻ｽ逧・↑谺關ｽ縺後≠繧九◆繧√∫函謌舌ｒ荳ｭ譁ｭ縺励∪縺励◆縲・, "error")
                return False
                
            # 霆ｽ蠕ｮ縺ｪ谺關ｽ縺ｪ繧峨、I縺ｫ陬懷ｮ後ｒ萓晞ｼ縺吶ｋ縲後そ繝ｫ繝輔Μ繝壹い縲阪ｒ霑ｽ蜉縺吶ｋ縺薙→繧ょ庄閭ｽ縺縺後・            # 迴ｾ迥ｶ縺ｯ繝ｦ繝ｼ繧ｶ繝ｼ縺ｸ縺ｮ隴ｦ蜻翫↓逡吶ａ縲∝・逅・・菴薙・邯咏ｶ壹ｒ險ｱ蜿ｯ縺吶ｋ縲・            if reporter: 
                reporter.report("笞・・縺・￥縺､縺九・鬆・岼縺ｫ荳崎ｶｳ縺後≠繧翫∪縺吶′縲∫函謌舌ｒ邯夊｡後＠縺ｾ縺吶・, "warning")
            return True

    async def expand_plots(
        self, book_id: int, target_ep_list: List[int], arcs: List[Any], 
        reporter=None, force: bool = False
    ) -> List[Any]:
        """蜷・ｩｱ縺ｮ繝ｭ繝ｼ繝峨・繝・・諠・ｱ繧貞・縺ｫ縲∬ｩｳ邏ｰ縺ｪ繧ｷ繝ｼ繝ｳ險ｭ險亥峙・・lueprint・峨ｒ逕滓・繝ｻ菫晏ｭ倥☆繧・""
        book = await self.engine.repo.get_book(book_id)
        bible = await self.engine.repo.get_latest_bible(book_id)
        if not book or not bible:
            return []

        # DB雋闕ｷ縺ｨAPI繝ｬ繝ｼ繝亥宛髯舌ｒ閠・・縺励◆蜷梧凾螳溯｡梧焚蛻ｶ髯・        sem = asyncio.Semaphore(3)
        results = []
        settings = bible.settings if isinstance(bible.settings, dict) else json.loads(bible.settings or "{}")
        roadmap = settings.get("full_story_roadmap", [])
        
        async def _process_episode(ep_num):
            async with sem:
                if not force:
                    existing = await self.engine.repo.get_plot(book_id, ep_num)
                    if existing and existing.detailed_blueprint and len(existing.detailed_blueprint) > 100:
                        return existing

                ep_info = next((r for r in roadmap if r.get("ep_num") == ep_num), {})
                past_plots = await self.engine.repo.get_plots_between(book_id, max(1, ep_num - 3), ep_num - 1)
                
                if not arcs:
                    logger.warning(f"笞・・[Warning] Ep.{ep_num} 螻暮幕: arcs縺檎ｩｺ縺ｧ縺・)

                try:
                    def _to_dict(obj):
                        if hasattr(obj, "model_dump"): return obj.model_dump()
                        if isinstance(obj, dict): return obj
                        return str(obj)
                    serializable_arcs = [_to_dict(a) for a in (arcs or [])]
                    
                    prompt = self.engine.pm.build_plot_expansion_prompt(
                        book.title, ep_num, ep_info, past_plots, serializable_arcs, book.genre
                    )
                    
                    res = await self.engine._generate_json(MODEL_PLOT_EXPANSION, prompt, response_schema=PlotEpisode)
                    if res.success:
                        p_data = PlotEpisode.model_validate(res.metadata)
                        await self.engine.repo.create_or_replace_plot(
                            book_id=book_id, ep_num=ep_num,
                            thought_process=p_data.thought_process,
                            title=p_data.title,
                            summary=p_data.one_line_summary,
                            detailed_blueprint=p_data.detailed_blueprint,
                            next_hook=p_data.next_hook.model_dump() if p_data.next_hook else {},
                            tension=p_data.tension,
                            stress=p_data.stress,
                            catharsis=p_data.catharsis,
                            love_meter=p_data.love_meter,
                            is_catharsis=p_data.is_catharsis,
                            catharsis_type=p_data.catharsis_type,
                            scenes=[s.model_dump() for s in p_data.scenes] if p_data.scenes else [],
                            status="expanded",
                            misunderstanding_gap=p_data.misunderstanding_gap,
                            lite_model_director_notes=p_data.lite_model_director_notes,
                            script_content=p_data.script_content,
                            current_chain_phase=p_data.current_chain_phase,
                            resolution_style=p_data.resolution_style,
                            burned_cost_or_loot=p_data.burned_cost_or_loot,
                            antagonist_status=p_data.antagonist_status,
                            thematic_milestone=p_data.thematic_milestone
                        )
                        if reporter:
                            reporter.report(f"統 隨ｬ{ep_num}隧ｱ 繝励Ο繝・ヨ隧ｳ邏ｰ蛹門ｮ御ｺ・ {p_data.title}", "info")
                        return p_data
                    else:
                        logger.error(f"Ep.{ep_num} API Error: {res.error_message}")
                        return None
                except Exception as e:
                    logger.error(f"笶・隨ｬ{ep_num}隧ｱ縺ｮ螻暮幕荳ｭ縺ｫ繧ｨ繝ｩ繝ｼ縺檎匱逕・ {e}", exc_info=True)
                    return {"ep_num": ep_num, "status": "failed_plot_gen", "error_message": str(e)}

        # gather繧剃ｽｿ逕ｨ縺励※螳牙・縺ｫ荳ｦ蛻怜ｮ溯｡・        tasks = [_process_episode(ep_num) for ep_num in target_ep_list]
        results = await asyncio.gather(*tasks)
        # None・亥､ｱ謨励お繝斐た繝ｼ繝会ｼ峨ｒ髯､螟悶＠縺ｦ霑斐☆
        return [r for r in results if r is not None]
        

    async def rebuild_hegemony_plot(
        self, book_id: int, start_ep: int, new_total_eps: int, keywords: str, trend_memo: str,
        plot_pattern_key: str, cost_severity: int, cheat_scale: int, system_assist: int, reporter=None
    ) -> List[Any]:
        book = await self.engine.repo.get_book(book_id)
        if not book:
            raise RuntimeError("菴懷刀縺瑚ｦ九▽縺九ｊ縺ｾ縺帙ｓ")

        past_chapters = await self.engine.repo.get_chapters_before(book_id, start_ep)
        pending_foreshadowing: List[str] = []
        if past_chapters:
            try:
                last_ws = past_chapters[0].world_state or {}
                if isinstance(last_ws, str):
                    last_ws = json.loads(last_ws)
                if isinstance(last_ws, dict):
                    pending_foreshadowing = last_ws.get("pending_foreshadowing", [])
            except Exception:
                pass

        if reporter:
            reporter.report(f"畑 隨ｬ{start_ep}隧ｱ縲懃ｬｬ{new_total_eps}隧ｱ縺ｮ繧｢繝ｼ繧ｯ蜀肴ｧ狗ｯ峨ｒ髢句ｧ・..", "info")

        prompt_outline = self.engine.pm.build_rebuild_plot_outline_prompt(book.title, start_ep, new_total_eps, book.synopsis, keywords, trend_memo, pending_foreshadowing)
        arc_res  = await self.engine._generate_json(MODEL_PLANNING, prompt_outline)
        new_arcs = arc_res.metadata.get("arcs", []) if arc_res.success else []

        bible = await self.engine.repo.get_latest_bible(book_id)
        if bible:
            settings_dict = bible.settings if isinstance(bible.settings, dict) else json.loads(bible.settings or "{}")
            old_arcs      = settings_dict.get("arcs", [])
            kept_arcs     = [a for a in old_arcs if isinstance(a, dict) and a.get("end_ep", 0) < start_ep]
            settings_dict["arcs"]          = kept_arcs + new_arcs
            settings_dict["cost_severity"] = cost_severity
            settings_dict["cheat_scale"]   = cheat_scale
            settings_dict["system_assist"] = system_assist
            await self.engine.repo.create_bible(book_id, settings_dict, (bible.version or 0) + 1, datetime.datetime.now().isoformat())

        await self.engine.repo.update_book_target_eps(book_id, new_total_eps)
        await self.engine.repo.delete_plots_from(book_id, start_ep)

        for ep in range(start_ep, new_total_eps + 1):
            await self.engine.repo.create_or_replace_plot(
                book_id=book_id, ep_num=ep,
                thought_process="",
                title="縲先悴逕滓・ (TBD)縲・,
                summary="縲後・繝ｭ繝・ヨ蜀肴ｧ狗ｯ峨肴ｩ溯・縺九ｉ蜍慕噪縺ｫ逕滓・縺励※縺上□縺輔＞縲・,
                detailed_blueprint="",
                next_hook="邯壹￥",
                tension=50, stress=0, catharsis=0, love_meter=0,
                is_catharsis=False, catharsis_type="縺ｪ縺・,
                scenes=[], status="planned",
                misunderstanding_gap="", lite_model_director_notes="",
                script_content="", current_chain_phase="Hate",
                resolution_style="Cheat",
                burned_cost_or_loot="縺ｪ縺・,
                antagonist_status="迴ｾ迥ｶ邯ｭ謖・,
                thematic_milestone="縺ｪ縺・
            )

        if reporter:
            reporter.report(f"売 隧ｳ邏ｰ繝励Ο繝・ヨ逕滓・繧帝幕蟋・({start_ep}縲悳new_total_eps}隧ｱ)...", "info")

        results = await self.expand_plots(
            book_id, list(range(start_ep, new_total_eps + 1)), new_arcs, reporter=reporter
        )
        return results

    async def audit_producer_plan(self, genre: str, keywords: str, trend_memo: str) -> Optional[HegemonyAuditResult]:
        """PlanningAgent蜀・〒AI繝励Ο繝・Η繝ｼ繧ｵ繝ｼ險ｺ譁ｭ繧貞ｮ溯｡・""
        prompt = self.engine.pm.build_producer_audit_prompt(genre, keywords, trend_memo)
        res = await self.engine._generate_json(MODEL_PLANNING, prompt, response_schema=HegemonyAuditResult, temp=0.4)
        if res.success:
            try:
                return HegemonyAuditResult.model_validate(res.metadata)
            except Exception:
                pass
        return None

class WritingAgent:
    """譛ｬ譁・濤遲・→繝代う繝励Λ繧､繝ｳ邂｡逅・ｒ諡・ｽ・""
    def __init__(self, engine: "UltimateHegemonyEngine"):
        self.engine = engine

    async def generate_episodes(
        self, book_id: int, start_ep: int, end_ep: int, passion: float, target_word_count: int,
        do_refine: bool, reporter=None, env_state: Optional[Dict[str, str]] = None,
        is_easy_mode: bool = False
    ) -> int:
        book   = await self.engine.repo.get_book(book_id)
        char_db_models = await self.engine.repo.get_all_characters(book_id)
        # DB繝｢繝・Ν繧偵∝ｱ樊ｧ繧｢繧ｯ繧ｻ繧ｹ縺悟庄閭ｽ縺ｪ Registry 繧ｪ繝悶ず繧ｧ繧ｯ繝医↓螟画鋤
        chars: List[CharacterRegistry] = []
        for cm in char_db_models:
            try:
                reg_data = cm.registry_data if isinstance(cm.registry_data, dict) else json.loads(cm.registry_data or "{}")
                chars.append(CharacterRegistry.model_validate(reg_data))
            except Exception:
                continue
        bible  = await self.engine.repo.get_latest_bible(book_id)
        bible_settings: Dict[str, Any] = {}
        if bible and bible.settings:
            bible_settings = bible.settings if isinstance(bible.settings, dict) else json.loads(bible.settings or "{}")

        style_dna_dict = json.loads(book.style_dna) if isinstance(book.style_dna, str) else (book.style_dna or {})
        style_key      = str(style_dna_dict.get("mode", "style_web_standard"))
        write_rule_type = str(style_dna_dict.get("rule_set", "RULE_SET_A"))
        genre_str      = book.genre if book and book.genre else "繝輔ぃ繝ｳ繧ｿ繧ｸ繝ｼ"
        
        is_light = is_light_style(style_key, genre_str)

        self.engine.current_ep_num = 0
        
        # 謾ｹ蝟・｡・: 遐皮｣ｨ謖・・繧呈怙蛻昴°繧峨す繧ｹ繝・Β謖・､ｺ縺ｫ邨ｱ蜷・        refine_direction = STYLE_REFINEMENT_DIRECTIONS["light" if is_light else "heavy"]
        commercial_inst = f"\n縲仙膚逕ｨ蝓ｷ遲・・繝ｭ繝医さ繝ｫ縲曾n{refine_direction}\n- 譁・ｭ玲焚縺ｮ豌ｴ蠅励＠縺ｧ縺ｯ縺ｪ縺上取緒蜀吶・隗｣蜒丞ｺｦ縲上〒逶ｮ讓吶ｒ驕疲・縺帙ｈ縲・n- 隱ｭ閠・・闊亥袖繧貞ｼ輔￥縲弱ヵ繝・け縲上ｒ蜷・す繝ｼ繝ｳ縺ｮ邨ゅｏ繧翫↓驟咲ｽｮ縺帙ｈ縲・

        integrity_monitor = PlotIntegrityMonitor(self.engine)
        logic_validator = InternalLogicValidator(self.engine)

        from engine_prompts import get_rule_set
        rule_set_content = get_rule_set(write_rule_type)
        style_inst       = self.engine.pm.get_style_instruction(style_key)

        current_stress   = book.cumulative_stress or 0
        total_len = 0

        for ep_num in range(start_ep, end_ep + 1):
            self.engine.current_ep_num = ep_num
            plot = await self.engine.repo.get_plot(book_id, ep_num)
            if not plot:
                continue

            stress_ctx = self.engine.narrative.compute_stress_phase(ep_num, current_stress, plot.is_catharsis, genre_str)
            phase_instruction = stress_ctx.get("instruction", "")
            force_catharsis = stress_ctx.get("force_catharsis", False)
            current_stress_for_episode = stress_ctx.get("next_stress", current_stress)

            static_ctx, dynamic_ctx, prev_ctx = await self.engine.ctx_mgr.get_optimal_context_split(book_id, ep_num, plot, chars)
            
            from engine_narrative import PacingGraph
            pacing = PacingGraph.get_instruction(ep_num, book.target_eps or 50, is_light)
            villain_inst = self.engine.pm.get_villain_instruction(genre_str)

            is_important_ep = plot.is_catharsis or force_catharsis or ep_num == 1
            settings_ctx = json.dumps(bible_settings, ensure_ascii=False)

            prev_prose = ""
            if ep_num > 1:
                prev_ch = await self.engine.repo.get_chapter(book_id, ep_num - 1)
                if prev_ch and prev_ch.content:
                    prev_prose = prev_ch.content[-500:].strip()

            atmo_prompt = AtmosphereGenerator.get_prompt(
                season=(env_state or {}).get("season", "譏･"),
                weather=(env_state or {}).get("weather", "譎ｴ螟ｩ"),
            )

            script_text = plot.script_content or ""
            p_dump      = plot.model_dump()

            if reporter:
                reporter.report(f"荘 隨ｬ{ep_num}隧ｱ [繧ｹ繝医Ξ繧ｹ:{current_stress_for_episode}]: 譛譁ｰ繧ｳ繝ｳ繝・く繧ｹ繝医〒蝓ｷ遲・幕蟋・, "info")

            # --- 謾ｹ蝟・｡・: Style RAG 縺ｫ繧医ｋ譁・ｽ薙し繝ｳ繝励Ν豕ｨ蜈･ ---
            style_rag = StyleRagManager(self.engine)
            # 繧ｷ繝ｼ繝ｳ險ｭ險亥峙繧貞・縺ｫ縲∵怙繧ゅ瑚ｳｪ諢溘阪′霑代＞繧ｵ繝ｳ繝励Ν繧呈､懃ｴ｢
            hegemony_sample_text = await style_rag.find_best_sample(
                plot.detailed_blueprint, 
                phase=plot.current_chain_phase,
                tag_hint=plot.catharsis_type if plot.is_catharsis else None
            )
            hegemony_inst = style_rag.format_as_prompt(hegemony_sample_text)

            current_target_word_count = target_word_count
            if is_important_ep:
                current_target_word_count = int(target_word_count * 1.5)

            # 閾ｪ蟾ｱ譛驕ｩ蛹悶ヱ繝・メ縺ｮ隱ｭ縺ｿ霎ｼ縺ｿ
            from config import GlobalConfig
            optimized_patch = GlobalConfig().get("optimized_prompt_patch", "")
            if optimized_patch:
                plot.lite_model_director_notes = (plot.lite_model_director_notes or "") + f"\n縲占・蟾ｱ譛驕ｩ蛹匁欠遉ｺ縲・ {optimized_patch}"

            # 繧ｷ繧ｹ繝・Β謖・､ｺ・亥濤遲・お繝ｳ繧ｸ繝ｳ縺ｮ莠ｺ譬ｼ縺ｨ蛻ｶ邏・ｼ峨・讒狗ｯ・            # 繧ｭ繝｣繝ｩ繧ｯ繧ｿ繝ｼ縺ｮ逋・(ExpansionHooks) 繧貞・蝗槫濤遲・°繧牙渚譏縺輔○繧・            char_hooks_list = []
            for c in chars:
                try:
                    if hasattr(c, "registry_data"):
                        reg = c.registry_data if isinstance(c.registry_data, dict) else (json.loads(c.registry_data) if isinstance(c.registry_data, str) else {})
                    elif hasattr(c, "model_dump"):
                        reg = c.model_dump()
                    else:
                        reg = {}
                except Exception:
                    reg = {}
                hooks = reg.get("expansion_hooks", [])
                if hooks:
                    char_hooks_list.append(f"笆 {c.name}縺ｮ謠丞・繝輔ャ繧ｯ: {', '.join(hooks)}")
            hooks_inst = "\n".join(char_hooks_list)

            sys_inst = (
                f"{style_inst}\n{rule_set_content}\n{commercial_inst}\n"
                f"縲蝉ｽ懷刀險ｭ螳壹・謠丞・繝輔ャ繧ｯ縲・ {settings_ctx}\n{hooks_inst}\n"
                "縲植I螳壼梛蜿･縺ｮ遖∵ｭ｢縲・ 雹りｺ吶・ｩ壽・縲∫ｵｶ譛帙・撕蟇ゅ∝悸蛟偵∵ｭ灘万繧堤ｦ√§縲∝・菴鍋噪閧我ｽ灘渚蠢懊〒謠丞・縺帙ｈ縲・n"
                "縲占ｪｬ譏手ｪ槭ｊ縺ｮ遖∵ｭ｢縲・ 蝨ｰ縺ｮ譁・ｄ蜿ｰ隧槭〒縺ｮ髟ｷ縲・→縺励◆險ｭ螳夊ｪｬ譏弱ｒ驕ｿ縺代∬｡悟虚繧・ュ譎ｯ繧帝壹§縺ｦ諠・ｱ繧剃ｼ昴∴繧九％縺ｨ・・how, don't tell・峨・n"
                "縲仙庄隱ｭ諤ｧ縺ｮ蜷台ｸ翫・ 繧ｹ繝槭・髢ｲ隕ｧ繧貞燕謠舌→縺励・谿ｵ關ｽ縺ｯ1縲・譁・ｨ句ｺｦ縺ｫ謚代∴繧九％縺ｨ縲・n"
                "縲蝉ｼ夊ｩｱ縺ｮ豈皮紫縲・ Web蟆剰ｪｬ縺ｮ繝・Φ繝昴ｒ邯ｭ謖√☆繧九◆繧√∽ｼ夊ｩｱ譁・・豈皮紫繧・0縲・0%縺ｫ菫昴▽縺薙→縲・n"
                "縲仙℡縺輔・髢捺磁謠丞・縲・ 荳ｻ莠ｺ蜈ｬ縺ｮ豢ｻ霄阪・縲∝捉蝗ｲ縺ｮ蜈ｷ菴鍋噪蜿榊ｿ懶ｼ亥｣ｰ縺ｮ髴・∴縲∝ｾ後★縺輔ｊ遲会ｼ峨ｒ逕ｨ縺・※髢捺磁逧・↓莨昴∴繧医・n"
                "縲仙ｼ輔″縺ｮ鄒主ｭｦ縲・ 譛蠕後・遏ｭ縺・堤ｽｮ豕輔ｄ菴楢ｨ豁｢繧√ｒ逕ｨ縺・∵ｬ｡繧定ｪｭ縺ｿ縺溘￥縺ｪ繧九主ｼ輔″縲上〒邱繧√ｋ縺薙→縲・
            )

            fw_prompt = self.engine.pm.build_final_writing_prompt(
                ep_num=ep_num,
                plot_data=p_dump,
                script_text=script_text,
                target_word_count=current_target_word_count,
                plot_thought_process=plot.thought_process,
                prose_sample=prev_prose, 
                settings_ctx=bible_settings, # Dict蠖｢蠑上〒貂｡縺・                char_static_ctx=static_ctx, char_dynamic_ctx=dynamic_ctx, prev_ctx=prev_ctx,
                is_climax=is_important_ep, 
                pacing_inst=pacing.get("instruction", ""),
                villain_inst=villain_inst,
                director_notes=(plot.lite_model_director_notes or "") + hegemony_inst,
            )
            fw_prompt += f"\n{atmo_prompt}"
            if plot.lite_model_director_notes:
                fw_prompt += f"\n縲絶國・・繝励Ο繝・ヨ譎ゅ・閾ｪ蟾ｱ謇ｹ蛻､繝ｻ菫ｮ豁｣謖・､ｺ縲曾n{plot.lite_model_director_notes}"
            if phase_instruction:
                fw_prompt += phase_instruction

            # --- 蝓ｷ遲・・逶｣隕悶Ν繝ｼ繝・(Regeneration Process) ---
            max_retries = 1 if is_easy_mode else 2
            final_content = ""
            final_meta = {}
            is_integrity_ok = True
            missing = []
            
            # 鬮倬溷喧蠕ｮ隱ｿ謨ｴ: 繝ｫ繝ｼ繝怜､悶〒荳蠎ｦ縺縺代く繝ｼ繝ｯ繝ｼ繝峨ｒ謚ｽ蜃ｺ・・PU繧ｳ繧ｹ繝亥炎貂幢ｼ・            blueprint_keywords = integrity_monitor.extract_keywords(plot.detailed_blueprint)

            for attempt in range(max_retries):
                # 1蝗樒岼縺ｯ邊ｾ蠎ｦ驥崎ｦ悶・蝗樒岼縺ｯ螟壽ｧ俶ｧ繧剃ｸ翫￡縺ｦ遯∫ｴ繧貞峙繧・                temp = 0.7 + (passion - 0.5) * 0.2 + (attempt * 0.15)
                final_res = await self.engine._generate_json(MODEL_WRITING, fw_prompt, system_instruction=sys_inst, temp=temp)
                final_meta, raw_content = final_res.unwrap_or({}, "")
                # Ensure metadata is normalized to a dict-like structure
                final_meta = OutputSanitizer.normalize_metadata(final_meta)

                # 鬮倬溘↑RegEx繝吶・繧ｹ縺ｮ謨ｴ蜷域ｧ繝√ぉ繝・け
                is_integrity_ok, rate, missing = await integrity_monitor.check_integrity(blueprint_keywords, plot.detailed_blueprint, raw_content)
                
                if is_easy_mode:
                    # 縺九ｓ縺溘ｓ繝｢繝ｼ繝・ 繝ｪ繝医Λ繧､縺帙★1蝗槭〒遒ｺ螳壹＆縺帙∽ｸ榊ｙ縺ｯ蠕檎ｶ壹・蜉遲・せ繝・ャ繝励∈蝗槭☆
                    final_content = self.engine.formatter.format_for_kakuyomu(raw_content)
                    break

                if is_integrity_ok:
                    # 騾壼ｸｸ蝗槭〒縺ｯ隲也炊讀懆ｨｼ繧偵せ繧ｭ繝・・縺励・㍾隕∝屓・・ayoff/Climax・峨・縺ｿ霑ｽ蜉讀懆ｨｼ
                    if is_important_ep and plot.misunderstanding_gap:
                        is_logic_ok, missing_steps = await logic_validator.validate_misunderstanding_flow(raw_content, plot.misunderstanding_gap)
                        if not is_logic_ok:
                            if reporter: reporter.report(f"圷 隲也炊遏帷崟讀懃衍 (Attempt {attempt+1}): {missing_steps}縲ょ・隧ｦ陦後＠縺ｾ縺吶・, "warning")
                            continue
                            
                    final_content = self.engine.formatter.format_for_kakuyomu(raw_content)
                    break
                else:
                    reason = f"謨ｴ蜷域ｧ邇・{rate*100:.0f}% (谺關ｽ: {', '.join(missing[:3])})"
                    if reporter:
                        reporter.report(f"圷 謨ｴ蜷域ｧ繧ｨ繝ｩ繝ｼ繧呈､懃衍 (Attempt {attempt+1}): {reason}縲ょｼｷ蛻ｶ蜀咲函謌舌ｒ螳溯｡後＠縺ｾ縺吶・, "warning")
                    if attempt == max_retries - 1:
                        final_content = self.engine.formatter.format_for_kakuyomu(raw_content) # 譛邨ゅΜ繝医Λ繧､螟ｱ謨・
            # 譁・ｭ玲焚荳崎ｶｳ縺ｾ縺溘・謨ｴ蜷域ｧ荳榊ｙ譎ゅ・閾ｪ蜍戊ｉ莉倥￠繝ｻ菫ｮ豁｣繝ｭ繧ｸ繝・け (縺九ｓ縺溘ｓ繝｢繝ｼ繝臥ｵｱ蜷・
            content_len = len(final_content)
            should_amplify = content_len > 100 and content_len < current_target_word_count * 0.85
            should_fix = is_easy_mode and not is_integrity_ok and content_len > 100

            if should_amplify or should_fix:
                if reporter: 
                    msg = "笞・・謠丞・荳崎ｶｳ繝ｻ謨ｴ蜷域ｧ繧剃ｸ諡ｬ陬懈ｭ｣荳ｭ..." if should_fix else "笞・・譁・ｭ玲焚荳崎ｶｳ縲よ緒蜀吶ｒ諡｡蠑ｵ荳ｭ..."
                    reporter.report(msg, "warning")
                
                # 謾ｹ蝟・ 谺關ｽ隕∫ｴ縺ｮ陬懈ｭ｣縺ｨ蜷梧凾縺ｫ縲√く繝｣繝ｩ繧ｯ繧ｿ繝ｼ蝗ｺ譛峨・縲檎剿(ExpansionHooks)縲阪ｒ蜿肴丐
                char_hooks = []
                for c in chars:
                    try:
                        if hasattr(c, "registry_data"):
                            reg = c.registry_data if isinstance(c.registry_data, dict) else (json.loads(c.registry_data) if isinstance(c.registry_data, str) else {})
                        elif hasattr(c, "model_dump"):
                            reg = c.model_dump()
                        else:
                            reg = {}
                    except Exception:
                        reg = {}
                    hooks = reg.get("expansion_hooks", [])
                    if hooks:
                        char_hooks.append(f"笆 {c.name}: {', '.join(hooks)}")
                hooks_inst = "\n縲舌く繝｣繝ｩ繧ｯ繧ｿ繝ｼ蝗ｺ譛峨・謠丞・繝輔ャ繧ｯ・亥ｿ・★蜿肴丐・峨曾n" + "\n".join(char_hooks) if char_hooks else ""
                
                fix_inst = f"\n縲宣㍾隕・ｼ壻ｻ･荳九・谺關ｽ隕∫ｴ繧貞ｿ・★蜷ｫ繧√※閾ｪ辟ｶ縺ｫ蜉遲・○繧医・ {', '.join(missing)}" if should_fix and missing else ""
                amplify_prompt = self.engine.pm.build_amplify_prompt(final_content, current_target_word_count, fix_inst + hooks_inst)

                res_amp = await self.engine._generate_json(MODEL_WRITING, amplify_prompt, temp=0.85)
                _, amp_content = res_amp.unwrap_or({}, final_content)
                final_content = self.engine.formatter.format_for_kakuyomu(amp_content)

            # 譛画ｩ溽噪邨仙粋: DB險ｭ螳壹↓蝓ｺ縺･縺阪√く繝｣繝ｩ繧ｯ繧ｿ繝ｼ縺ｮ蜿｣隱ｿ繝ｻ莠ｺ遘ｰ繧呈怙邨ょｼｷ蛻ｶ陬懈ｭ｣
            final_content = TonePerfector.enforce_tone(final_content, chars)

            if ep_num == 1:
                catharsis_errors = ContentValidator.check_catharsis_reservation(final_content, ep_num)
                for err in catharsis_errors:
                    if reporter:
                        reporter.report(err, "warning")
                    logger.warning(f"Catharsis check failed for Ep.1: {err}")

            rhythm_errors = ContentValidator.check_rhythm(final_content)
            if rhythm_errors:
                if reporter:
                    reporter.report("棟 繝ｪ繧ｺ繝蜊倩ｪｿ縺輔ｒ讀懃衍縲り・蜍戊｣懈ｭ｣繧貞ｮ溯｡後＠縺ｾ縺・..", "warning")
                original_before_rhythm = final_content
                final_content = ContentValidator.auto_correct_rhythm(final_content)
                tone_errors   = verify_character_tone(original_before_rhythm, final_content)
                for err in tone_errors:
                    if reporter:
                        reporter.report(err, "warning")

            # 謾ｹ蝟・｡・: Payoff繝輔ぉ繝ｼ繧ｺ縺ｾ縺溘・驥崎ｦ∝屓縺ｮ縺ｿ蜴ｳ蟇・↑逶｣譟ｻ繧定｡後≧・医◎繧御ｻ･螟悶・繧ｹ繧ｭ繝・・縺励※鬮倬溷喧・・            should_deep_audit = is_important_ep or plot.current_chain_phase == "Payoff"
            if reporter and should_deep_audit:
                reporter.report(f"剥 隨ｬ{ep_num}隧ｱ 迚ｩ隱槭・謨ｴ蜷域ｧ繧偵メ繧ｧ繝・け荳ｭ...", "info")

            f_audit = await self.engine.auditor.audit_foreshadowing_payoff(book_id, ep_num, final_content) if should_deep_audit else ForeshadowingAudit(is_recovered=True)
            audit_log_data = {}

            if should_deep_audit:
                if not f_audit.is_recovered and f_audit.missing_items:
                    # 謾ｹ蝟・｡・: 閾ｪ蜍輔Μ繝医Λ繧､・域嶌縺咲峩縺暦ｼ峨ｒ蟒・ｭ｢縺励√Θ繝ｼ繧ｶ繝ｼ縺ｸ縺ｮ隴ｦ蜻翫・縺ｿ縺ｫ縺吶ｋ
                    reporter.report(f"笞・・莨冗ｷ壽悴蝗槫庶繧呈､懃衍縺励∪縺励◆縲ゅ・繝ｭ繝・ヨ險ｭ險亥峙繧堤｢ｺ隱阪＠縺ｦ縺上□縺輔＞: {', '.join(f_audit.missing_items)}", "warning")
                audit_log_data = f_audit.model_dump()
                audit_log_data = OutputSanitizer.normalize_metadata(audit_log_data)
            else:
                prev_chapter = await self.engine.repo.get_chapter(book_id, ep_num - 1)
                prev_ws = None
                if prev_chapter and prev_chapter.world_state:
                    try:
                        prev_ws_dict = prev_chapter.world_state if isinstance(prev_chapter.world_state, dict) else json.loads(prev_chapter.world_state)
                        prev_ws = WorldState.model_validate(prev_ws_dict)
                    except Exception as e:
                        logger.warning(f"Failed to parse previous world state for lightweight audit: {e}")

                current_ws_dict = final_meta.get("next_world_state", {})
                current_ws = WorldState.model_validate(current_ws_dict)

                light_audit = await self.engine.auditor.lightweight_audit_world_state(current_ws, prev_ws)
                if not light_audit.is_consistent:
                    for conflict in light_audit.conflict_points:
                        reporter.report(f"笞・・霆ｽ驥冗屮譟ｻ隴ｦ蜻・ {conflict}", "warning")
                audit_log_data = light_audit.model_dump()
                audit_log_data = OutputSanitizer.normalize_metadata(audit_log_data)

            total_len += len(final_content)

            stress_delta = int(final_meta.get("stress_delta", 0) / 10)
            current_stress = max(0, current_stress_for_episode + stress_delta)
            await self.engine.repo.update_book_cumulative_stress(book_id, current_stress)

            if reporter:
                reporter.update_progress(
                    ep_num - start_ep + 1, end_ep - start_ep + 1,
                    f"隨ｬ{ep_num}隧ｱ 螳御ｺ・({len(final_content)}譁・ｭ・ [繧ｹ繝医Ξ繧ｹ竊畜current_stress}]"
                )

            await self.engine.repo.create_chapter(
                book_id, ep_num,
                p_dump.get("title", f"隨ｬ{ep_num}隧ｱ"),
                final_content,
                final_meta.get("summary", ""),
                None,
                f"Completed [stress:{current_stress}]" + (f" [Audit:{audit_log_data.get('audit_type', 'L')}]" if not audit_log_data.get('is_consistent', True) else ""),
                final_meta.get("next_world_state", {}),
                {"note": "Ultimate Pipeline + StressLoop", "audit_log": audit_log_data},
                time.strftime('%Y-%m-%dT%H:%M:%S'),
            )
            await self.engine.repo.update_plot_status_stress_love(
                book_id, ep_num, current_stress, final_meta.get("love_delta", 0)
            )

        return total_len

    async def generate_episodes_pipeline(self, book_id: int, start_ep: int, end_ep: int, passion: float, target_word_count: int, reporter=None, is_easy_mode: bool = False) -> Tuple[int, List[Dict[str, Any]]]:
        # 繧ｭ繝･繝ｼ繧ｵ繧､繧ｺ繧貞ｺ・￡縲∝・陦後＠縺ｦ繝励Ο繝・ヨ繧剃ｽ懊ｌ繧九ｈ縺・↓縺吶ｋ
        plot_queue = asyncio.Queue() # Unbounded queue for maximum throughput
        from config import GlobalConfig
        cfg = GlobalConfig()
        configured_concurrency = cfg.get("max_concurrency", 0) # 0 means auto
        write_sem_value = configured_concurrency if configured_concurrency > 0 else (2 if is_easy_mode else 1)
        write_sem  = asyncio.Semaphore(write_sem_value)
        
        total_chars = [0] # Use a list to allow modification in nested async functions
        stop_event = asyncio.Event()
        bible = await self.engine.repo.get_latest_bible(book_id)
        settings = bible.settings if isinstance(bible.settings, dict) else json.loads(bible.settings or "{}") if bible else {}
        arcs = settings.get("arcs", [])

        async def plotter():
            failed_plot_generations = [] # Collect failures from plotter
            # 繝励Ο繝・ヨ縺ｨ蝓ｷ遲・ｸ医∩繝√Ε繝励ち繝ｼ繧偵せ繧ｭ繝｣繝ｳ縺励※菫ｮ蠕ｩ縺悟ｿ・ｦ√↑繧ゅ・繧堤音螳・            existing_plots = await self.engine.repo.get_plots_between(book_id, start_ep, end_ep)
            chapters = await self.engine.repo.get_all_non_anchor_chapters(book_id)
            chap_nums = {c.ep_num for c in chapters}
            
            plots_to_generate = []
            for ep in range(start_ep, end_ep + 1):
                if ep in chap_nums:
                    continue # 譌｢縺ｫ譛ｬ譁・′縺ゅｋ蝣ｴ蜷医・繧ｹ繧ｭ繝・・
                
                # 繝√Ε繝励ち繝ｼ縺後↑縺・ｴ蜷医∵里蟄倥・繝ｭ繝・ヨ縺ｮ譛臥┌繧堤｢ｺ隱・                plot = next((p for p in existing_plots if p.ep_num == ep), None)
                if plot and plot.detailed_blueprint and len(plot.detailed_blueprint) > 100:
                    # 繝励Ο繝・ヨ縺後≠繧九↑繧牙叉蠎ｧ縺ｫ蝓ｷ遲・く繝･繝ｼ縺ｸ
                    await plot_queue.put(plot)
                    if reporter: reporter.report(f"唐 譌｢蟄倥・繝ｭ繝・ヨ繧貞茜逕ｨ: 隨ｬ{ep}隧ｱ", "info")
                else:
                    # 繝励Ο繝・ヨ繧ゅ↑縺・↑繧臥函謌仙ｯｾ雎｡縺ｸ
                    plots_to_generate.append(ep)

            # 繝励Ο繝・ヨ逕滓・閾ｪ菴薙ｒ荳ｦ陦後ち繧ｹ繧ｯ縺ｨ縺励※邂｡逅・☆繧・            plot_tasks = []
            try:
                async def _produce_plot(ep_num):
                    if stop_event.is_set(): return
                    if reporter: reporter.report(f"亮・・繝励Ο繝・ヨ逕滓・荳ｭ: 隨ｬ{ep_num}隧ｱ", "info")
                    try:
                        p_res = await self.engine.planner.expand_plots(book_id, [ep_num], arcs, reporter=reporter, force=False)
                        if p_res:
                            if p_res[0].get("status") == "failed_plot_gen": # Check for failure indicator
                                failed_plot_generations.append(p_res[0])
                                if reporter: reporter.report(f"笞・・繝励Ο繝・ヨ逕滓・螟ｱ謨・ 隨ｬ{ep_num}隧ｱ ({p_res[0]['error_message']})", "warning")
                            else:
                                await plot_queue.put(p_res[0])
                                if reporter: reporter.report(f"笨・繝励Ο繝・ヨ逕滓・螳御ｺ・ 隨ｬ{ep_num}隧ｱ", "info")
                    except asyncio.CancelledError:
                        logger.info(f"Plot generation for ep {ep_num} was cancelled.")
                        failed_plot_generations.append({"ep_num": ep_num, "status": "cancelled", "error_message": "Plot generation cancelled."})
                    except Exception as e:
                        logger.error(f"Error producing plot for ep {ep_num}: {e}")
                        failed_plot_generations.append({"ep_num": ep_num, "status": "failed_plot_gen", "error_message": str(e)})

                # 縺吶∋縺ｦ縺ｮ隧ｱ謨ｰ縺ｮ繝励Ο繝・ヨ逕滓・繧剃ｸｦ陦後＠縺ｦ髢句ｧ具ｼ亥・驛ｨ縺ｧSemaphore(4)縺悟柑縺擾ｼ・                tasks = [asyncio.create_task(_produce_plot(ep)) for ep in plots_to_generate]
                plot_tasks.extend(tasks)
                await asyncio.gather(*tasks)
                
                await plot_queue.put(None)
            except Exception as e:
                stop_event.set()
                await plot_queue.put(e)
                if reporter:
                    reporter.report(f"Plotter Error (Critical): {e}", "error")
            finally:
                # Add any remaining failed plot generations to the queue for the writer to process
                for failure in failed_plot_generations:
                    await plot_queue.put(failure)
                # Ensure the writer knows plotter is done
                await plot_queue.put(None)

        failed_episodes = [] # Collect all failed episodes (plot gen or writing)

        async def writer():
            try:
                while True:
                    item = await plot_queue.get()
                    if stop_event.is_set() or (reporter and reporter.state.should_stop()): break
                    if item is None: break
                    
                    if isinstance(item, dict) and item.get("status") == "failed_plot_gen":
                        failed_episodes.append(item)
                        if reporter: reporter.report(f"笞・・隨ｬ{item['ep_num']}隧ｱ縺ｮ蝓ｷ遲・ｒ繧ｹ繧ｭ繝・・ (繝励Ο繝・ヨ逕滓・螟ｱ謨・", "warning")
                        plot_queue.task_done()
                        continue
                    elif isinstance(item, Exception): # If a raw exception somehow gets through
                        failed_episodes.append({"ep_num": "Unknown", "status": "critical_error", "error_message": str(item)})
                        if reporter: reporter.report(f"圷 繝代う繝励Λ繧､繝ｳ縺ｧ莠域悄縺帙〓繧ｨ繝ｩ繝ｼ縺檎匱逕・ {item}", "error")
                        stop_event.set() # Stop the pipeline on critical unhandled exception
                        continue
                    
                    # ep_num 繧堤｢ｺ螳溘↓蜿門ｾ・                    ep = item.get("ep_num") if isinstance(item, dict) else getattr(item, 'ep_num', None)
                    if ep is None: continue # Should not happen with proper plotter failure handling

                    if reporter: reporter.report(f"笨搾ｸ・譛ｬ譁・濤遲・ｸｭ: 隨ｬ{ep}隧ｱ", "info")
                    async with write_sem:
                        chars_count = await self.generate_episodes(book_id, ep, ep, passion, target_word_count, True, reporter, is_easy_mode=is_easy_mode)
                        total_chars[0] += chars_count
                    plot_queue.task_done()
            except Exception as e:
                logger.error(f"Writer Error at ep {ep if 'ep' in locals() else 'unknown'}: {e}")
                failed_episodes.append({"ep_num": ep, "status": "failed_writing", "error_message": str(e)})
                if is_easy_mode:
                    if reporter: reporter.report(f"笞・・隨ｬ{ep}隧ｱ縺ｮ蝓ｷ遲・ｸｭ縺ｫ繧ｨ繝ｩ繝ｼ縺檎匱逕溘＠縺ｾ縺励◆縺後∫ｶ夊｡後＠縺ｾ縺吶・, "warning")
                    # 繧ｭ繝･繝ｼ縺ｮ迥ｶ諷九ｒ豁｣蟶ｸ蛹悶＠縺ｦ邯夊｡・                    try: plot_queue.task_done()
                    except: pass
                else:
                    stop_event.set()
                    if reporter: reporter.report(f"Writer Error: {e}", "error")
                    raise

        try:
            await asyncio.gather(plotter(), writer())
        except Exception as e:
            logger.error(f"Pipeline final error: {e}")
            
        return total_chars[0], failed_episodes

    async def analyze_and_import_chapter(self, book_id: int, ep_num: int, content: str, do_refine: bool = False) -> Dict[str, Any]:
        try:
            cleaned_content = self.engine.formatter.format_for_kakuyomu(content)
            book  = await self.engine.repo.get_book(book_id)
            if not book:
                return {"error": "菴懷刀縺瑚ｦ九▽縺九ｊ縺ｾ縺帙ｓ"}
            plot  = await self.engine.repo.get_plot(book_id, ep_num)
            prompt = self.engine.pm.build_analyze_import_chapter_prompt(cleaned_content, EpisodeDraft)
            res = await self.engine._generate_json(MODEL_PLANNING, prompt, response_schema=EpisodeDraft)
            if res.success:
                data = res.metadata
                # 菫晏ｭ伜・逅・                await self.engine.repo.create_chapter(
                    book_id, ep_num, data.get("title", f"隨ｬ{ep_num}隧ｱ"),
                    cleaned_content, data.get("summary", ""),
                    None, "Imported", data.get("next_world_state", {}),
                    {"note": "Imported via analyze_and_import_chapter"},
                    time.strftime('%Y-%m-%dT%H:%M:%S')
                )
                return data
            return {"error": "蛻・梵縺ｫ螟ｱ謨励＠縺ｾ縺励◆"}
        except Exception as e:
            return {"error": str(e)}

