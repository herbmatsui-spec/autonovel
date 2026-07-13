import asyncio
import datetime
import io
import json
import logging
import re
import time
import zipfile
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from backend.engine_style_rag import StyleRagManager
from backend.engine_utils import is_light_style, safe_model_validate, verify_character_tone
from backend.sanitizer import AtmosphereGenerator, ContentValidator, OutputSanitizer, TonePerfector
from config import (
    MODEL_PLANNING,
    MODEL_PLOT_EXPANSION,
    MODEL_WRITING,
    STYLE_REFINEMENT_DIRECTIONS,
)
from models import (
    CharacterRegistry,
    EpisodeDraft,
    ForeshadowingAudit,
    HegemonyAuditResult,
    LogicalAuditResult,
    PlotEpisode,
    RoadmapList,
    StyleDNA,
    WorldBible,
    WorldBibleCore,
    WorldRules,
    WorldState,
)

if TYPE_CHECKING:
    from backend.engine import UltimateHegemonyEngine

logger = logging.getLogger(__name__)

# ==========================================
# BaseAgent (共通インターフェース)
# ==========================================
class BaseAgent:
    """全エージェントの基底クラス"""
    def __init__(self, engine: "UltimateHegemonyEngine"):
        self.engine = engine

class LogicalAuditor(BaseAgent):
    """物語の整合性と伏線回収の監査を担当"""

    async def audit_plot(self, book_id: int, ep_num: int, plot_bp: str, script: str) -> LogicalAuditResult:
        # 改善案3: 履歴取得を ContextManager に一元化
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
        """簡易的な状態矛盾チェック"""
        if not previous: return LogicalAuditResult(is_consistent=True)
        conflicts = []
        for char, state in current.character_states.items():
            prev_state = previous.character_states.get(char, "")
            if "死亡" in prev_state and "生存" in state:
                conflicts.append(f"矛盾検知: {char} が前話で死亡していますが、今話で生存状態になっています。")
        if conflicts: return LogicalAuditResult(is_consistent=False, conflict_points=conflicts, severity="Major")
        return LogicalAuditResult(is_consistent=True)

class InternalLogicValidator(BaseAgent):
    """
    『勘違い』プロセスの論理的整合性を厳密に検証する。
    事実(A) -> 絶望(B) -> 誤認(C) -> 覚醒(D) の4ステップを検証。
    """
    async def validate_misunderstanding_flow(self, content: str, gap_desc: str) -> Tuple[bool, List[str]]:
        prompt = (
            self.engine.pm.build_misunderstanding_validation_prompt(content, gap_desc)
        )
        res = await self.engine._generate_json(MODEL_PLANNING, prompt, temp=0.2)
        meta = res.metadata if res.success else {}
        return meta.get("passed", True), meta.get("missing_steps", [])

class PlotIntegrityMonitor(BaseAgent):
    """
    設計図（Blueprint）と本文の物理的一致を監視。
    重要アイテム、音、動作の出現率が80%未満なら再生成をトリガー。
    """
    def extract_keywords(self, blueprint: str) -> List[str]:
        """設計図から重要キーワードを抽出する（キャッシュ用）"""
        if not blueprint: return []
        # 「」や『』で囲まれた単語、および2文字以上の漢字・カタカナを抽出
        keywords = re.findall(r'「(.*?)」|『(.*?)』', blueprint)
        keywords = [k[0] or k[1] for k in keywords if k[0] or k[1]]
        # 補助的に2文字以上の漢字・カタカナも追加
        ja_keywords = re.findall(r'[一-龠々]{2,}|[ァ-ヶー]{2,}', blueprint)
        keywords.extend(ja_keywords)
        # 重複排除とクリーニング
        return list(set([k.strip() for k in keywords if k.strip()]))[:15]

    async def check_integrity(self, keywords: List[str], blueprint: str, content: str) -> Tuple[bool, float, List[str]]:
        """物理的な一致確認"""
        if not keywords: return True, 1.0, []

        # 2. 本文内での出現チェック
        found = []
        missing = []
        for kw in keywords:
            if kw in content:
                found.append(kw)
            else:
                missing.append(kw)

        hit_rate = len(found) / len(keywords)
        is_ok = hit_rate >= 0.8

        # 重要アイテム（設計図で強調されているもの）の消失チェック
        critical_missing = [m for m in missing if f"重要:{m}" in blueprint or f"必須:{m}" in blueprint]
        if critical_missing: is_ok = False

        return is_ok, hit_rate, missing

class MarketingAgent:
    """宣伝パック、タイトル、文体DNAの分析と生成を担当"""
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
        return ["覇権の始まり", "追放された最強者", "全てを超えし者"]

    async def analyze_style_dna(self, sample_text: str) -> Dict[str, Any]:
        prompt = self.engine.pm.build_style_dna_analysis_prompt(sample_text)
        res = await self.engine._generate_json(MODEL_PLANNING, prompt, temp=0.3, response_schema=StyleDNA)
        return res.metadata if res.success else {"name": "分析失敗", "instruction": "", "score": 0, "analysis": ""}

    async def create_export_package(self, book_id: int) -> Tuple[bytes, str]:
        """作品データ一式（本文、設定、プロット、JSONダンプ）をZIPパッケージ化する"""
        book = await self.engine.repo.get_book(book_id)
        if not book: raise ValueError("作品が見つかりません。")

        chapters = await self.engine.repo.get_all_non_anchor_chapters(book_id, order_by="ep_num")
        chars    = await self.engine.repo.get_all_characters(book_id)
        bible    = await self.engine.repo.get_latest_bible(book_id)
        plots    = await self.engine.repo.get_all_plots(book_id)

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            # 01: 本文
            full_text = "".join(f"第{c.ep_num}話 {c.title}\n\n{c.content}\n\n" for c in chapters)
            z.writestr("01_本文.txt", full_text)

            # 02: キャラクター・世界観設定
            settings_str = ""
            if bible and bible.settings:
                settings_str = json.dumps(bible.settings, ensure_ascii=False, indent=2) if isinstance(bible.settings, dict) else str(bible.settings)

            setting_text = f"【世界観設定】\n{settings_str}\n\n"
            setting_text += "【キャラクター設定】\n"
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
                setting_text += f"■ {c.name} ({c.role})\n性格: {reg.get('personality', '')}\n能力: {reg.get('ability', '')}\n\n"
            z.writestr("02_キャラクター・世界観設定集.txt", setting_text)

            # 03: 作品登録用データ
            mkt = book.marketing_data if isinstance(book.marketing_data, dict) else {}
            reg_text = (
                f"【タイトル】\n{book.title}\n\n"
                f"【あらすじ】\n{book.synopsis or ''}\n\n"
                f"【キャッチコピー】\n{', '.join(mkt.get('catchcopies', [])) if mkt.get('catchcopies') else ''}\n\n"
                f"【タグ】\n{', '.join(mkt.get('tags', [])) if mkt.get('tags') else ''}\n"
            )
            z.writestr("03_作品登録用データ.txt", reg_text)

            # 04: 全話プロット構成案
            plot_text = "【全話プロット構成案】\n\n"
            for p in plots:
                plot_text += f"第{p.ep_num}話：{p.title}\n"
                if p.summary: plot_text += f"  一行あらすじ：{p.summary}\n"
                plot_text += f"【設計図】\n{p.detailed_blueprint}\n"
                if p.next_hook:
                    hook_desc = p.next_hook
                    if isinstance(p.next_hook, dict): hook_desc = p.next_hook.get('description', '')
                    plot_text += f"【次回への引き】\n{hook_desc}\n"
                plot_text += "\n" + "-"*30 + "\n\n"
            z.writestr("04_全話プロット構成案.txt", plot_text)

            # 05: JSONダンプ
            dump_data = {
                "book": book.model_dump(),
                "bible": bible.model_dump() if bible else {},
                "plots": [p.model_dump() for p in plots],
                "chapters": [c.model_dump() for c in chapters],
            }
            z.writestr("05_作品データダンプ.json", json.dumps(dump_data, ensure_ascii=False, indent=2))

        return buf.getvalue(), f"{book.title}_覇権作品.zip"

class PlanningAgent:
    """覇権企画の立案と再構築を担当"""
    def __init__(self, engine: "UltimateHegemonyEngine"):
        self.engine = engine

    async def create_hegemony_plan(
        self, genre: str, keywords: str, style_key: str, concept: str, title: str,
        cheat_scale: int, growth_curve: str, system_assist: int, cost_severity: int,
        target_eps: int, initial_plot_limit: int, reporter=None,
    ) -> Tuple[int, WorldBible]:
        if reporter:
            reporter.report("🌍 世界観の深層生成を開始...", "info")

        world_prompt = self.engine.pm.build_world_creation_prompt(genre, keywords, WorldRules)

        world_res = await self.engine._generate_json(MODEL_PLANNING, world_prompt, response_schema=WorldRules, temp=0.8)
        if not world_res.success:
            logger.warning(f"世界観設定の生成に失敗しました。デフォルト設定を使用します: {world_res.error_message}")
            world_rules = WorldRules()
        else:
            world_rules = WorldRules.model_validate(world_res.metadata)

        if reporter:
            reporter.report("🦸 主人公（MC）を個別造形中...", "info")

        mc_prompt = self.engine.pm.build_mc_creation_prompt(
            world_rules.model_dump_json(), genre, keywords, concept
        )

        mc_res = await self.engine._generate_json(MODEL_PLANNING, mc_prompt, temp=0.8)
        if not mc_res.success:
            logger.warning(f"主人公の生成に失敗しました: {mc_res.error_message}")
        mc_data = mc_res.metadata or {}
        # MCの名前をサブキャラ生成プロンプトに渡すために抽出
        mc_name = mc_data.get("name", "")

        if reporter:
            reporter.report("👥 サブキャラクター群を一括召喚中...", "info")

        # 改善: 世界観の因果律(causality_map)を直接注入し、世界と密接に関わるキャラを生成
        sub_prompt = self.engine.pm.build_sub_char_creation_prompt(
            world_rules.model_dump_json(), json.dumps(mc_data, ensure_ascii=False), world_rules.causality_map,
            mc_name
        )
        sub_res = await self.engine._generate_json(MODEL_PLANNING, sub_prompt, temp=0.8)
        if not sub_res.success:
            logger.warning(f"サブキャラクターの生成に失敗しました: {sub_res.error_message}")
        subs_data = sub_res.metadata.get("characters", [])

        if reporter:
            reporter.report("📋 企画書を統合中...", "info")
        bible_prompt = self.engine.pm.build_bible_creation_prompt(WorldBibleCore, world_rules.model_dump_json(), concept or genre + 'の覇権作品', target_eps)
        bible_res  = await self.engine._generate_json(MODEL_PLANNING, bible_prompt, response_schema=WorldBibleCore)
        if not bible_res.success:
            raise RuntimeError(f"コア設定生成失敗: {bible_res.error_message}")
        bible_core = WorldBibleCore.model_validate(bible_res.metadata)
        bible_core.world_settings = world_rules
        if mc_data:
            try:
                normalized_mc = OutputSanitizer.normalize_metadata(mc_data)
                bible_core.mc_profile = CharacterRegistry.model_validate(normalized_mc)
            except Exception:
                logger.error("MCプロフィールのバリデーションに失敗しました（データ構造不一致）")
        if subs_data:
            try:
                bible_core.sub_characters = [CharacterRegistry.model_validate(OutputSanitizer.normalize_metadata(s)) for s in subs_data[:5]]
            except Exception:
                logger.error("サブキャラクターのバリデーションに失敗しました（データ構造不一致）")
        if title:
            bible_core.title = title

        if reporter:
            reporter.report("📊 タイトル・タグのABテスト中...", "info")
        mkt_prompt = self.engine.pm.build_marketing_ab_test_prompt(bible_core.concept)
        mkt_res = await self.engine._generate_json(MODEL_PLANNING, mkt_prompt)
        if mkt_res.success and "ab_test_candidates" in mkt_res.metadata:
            win = mkt_res.metadata["ab_test_candidates"][mkt_res.metadata.get("winning_index", 0)]
            bible_core.title                           = win.get("title", bible_core.title)
            bible_core.marketing_assets.tags           = win.get("tags", [])
            bible_core.marketing_assets.ab_test_candidates = mkt_res.metadata["ab_test_candidates"]
            if reporter:
                reporter.report(f"🏆 最強タイトル決定: 『{bible_core.title}』", "info")

        if reporter:
            reporter.report("🗺️ 全話ロードマップを構築中...", "info")
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
            reporter.report(f"✅ 企画保存完了 (ID: {book_id})。執筆パイプラインを準備中...", "info")

        # initial_plot_limitが指定されている場合のみ展開（かんたんモードでは0を指定してパイプラインへ流す）
        if initial_plot_limit > 0:
            await self.expand_plots(
                book_id, list(range(1, initial_plot_limit + 1)), bible_obj.arcs, reporter=reporter
            )
        return book_id, bible_obj

    async def audit_bible_completeness(self, bible: WorldBible, reporter=None) -> bool:
        """
        詳細プロット展開前に、企画書（Bible）の重要項目に抜け漏れがないかチェックする。
        不備がある場合は警告を出し、致命的な場合は False を返す。
        """
        if reporter:
            reporter.report("🔍 企画書の整合性・完備性を最終チェック中...", "info")

        issues = []

        # 1. 基本情報のチェック
        if not bible.title or "無題" in bible.title: issues.append("作品タイトルが未設定です。")
        if len(bible.synopsis) < 200: issues.append("全体あらすじの書き込みが不足しています。")

        # 2. キャラクターのチェック
        mc = bible.mc_profile
        if not mc.name: issues.append("主人公の名前が設定されていません。")

        # registry_data の構造を模したチェック（CharacterRegistryオブジェクトとして評価）
        if not mc.expansion_hooks:
            issues.append(f"主人公 {mc.name} の『描写フック(Expansion Hooks)』が空です。執筆の質が低下する恐れがあります。")
        if not mc.first_person: issues.append(f"主人公 {mc.name} の一人称が未設定です。")

        # 3. 世界観・ロードマップのチェック
        if not bible.world_settings.causality_map:
            issues.append("世界の因果律（Causality Map）が空です。展開がご都合主義になるリスクがあります。")

        roadmap_len = len(bible.full_story_roadmap)
        if roadmap_len == 0:
            issues.append("全話ロードマップが生成されていません。詳細プロットへ進めません。")

        if not issues:
            if reporter: reporter.report("✨ 企画書の健全性チェック合格。プロット詳細化へ移行します。", "info")
            return True
        else:
            for issue in issues:
                logger.warning(f"[Bible Audit] {issue}")
                if reporter: reporter.report(issue, "warning")

            # 致命的な欠落（ロードマップなし）がある場合のみ中断
            if roadmap_len == 0:
                if reporter: reporter.report("🚨 致命的な欠落があるため、生成を中断しました。", "error")
                return False

            # 軽微な欠落なら、AIに補完を依頼する「セルフリペア」を追加することも可能だが、
            # 現状はユーザーへの警告に留め、処理自体は継続を許可する。
            if reporter:
                reporter.report("⚠️ いくつかの項目に不足がありますが、生成を続行します。", "warning")
            return True

    async def expand_plots(
        self, book_id: int, target_ep_list: List[int], arcs: List[Any],
        reporter=None, force: bool = False
    ) -> List[Any]:
        """各話のロードマップ情報を元に、詳細なシーン設計図（Blueprint）を生成・保存する"""
        book = await self.engine.repo.get_book(book_id)
        bible = await self.engine.repo.get_latest_bible(book_id)
        if not book or not bible:
            return []

        # DB負荷とAPIレート制限を考慮した同時実行数制限
        sem = asyncio.Semaphore(3)
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
                    logger.warning(f"⚠️ [Warning] Ep.{ep_num} 展開: arcsが空です")

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
                            reporter.report(f"📝 第{ep_num}話 プロット詳細化完了: {p_data.title}", "info")
                        return p_data
                    else:
                        logger.error(f"Ep.{ep_num} API Error: {res.error_message}")
                        return None
                except Exception as e:
                    logger.error(f"❌ 第{ep_num}話の展開中にエラーが発生: {e}", exc_info=True)
                    return {"ep_num": ep_num, "status": "failed_plot_gen", "error_message": str(e)}

        # gatherを使用して安全に並列実行
        tasks = [_process_episode(ep_num) for ep_num in target_ep_list]
        results = await asyncio.gather(*tasks)
        # None（失敗エピソード）を除外して返す
        return [r for r in results if r is not None]


    async def rebuild_hegemony_plot(
        self, book_id: int, start_ep: int, new_total_eps: int, keywords: str, trend_memo: str,
        plot_pattern_key: str, cost_severity: int, cheat_scale: int, system_assist: int, reporter=None
    ) -> List[Any]:
        book = await self.engine.repo.get_book(book_id)
        if not book:
            raise RuntimeError("作品が見つかりません")

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
            reporter.report(f"🔨 第{start_ep}話〜第{new_total_eps}話のアーク再構築を開始...", "info")

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
                title="【未生成 (TBD)】",
                summary="「プロット再構築」機能から動的に生成してください。",
                detailed_blueprint="",
                next_hook="続く",
                tension=50, stress=0, catharsis=0, love_meter=0,
                is_catharsis=False, catharsis_type="なし",
                scenes=[], status="planned",
                misunderstanding_gap="", lite_model_director_notes="",
                script_content="", current_chain_phase="Hate",
                resolution_style="Cheat",
                burned_cost_or_loot="なし",
                antagonist_status="現状維持",
                thematic_milestone="なし"
            )

        if reporter:
            reporter.report(f"🔄 詳細プロット生成を開始 ({start_ep}〜{new_total_eps}話)...", "info")

        results = await self.expand_plots(
            book_id, list(range(start_ep, new_total_eps + 1)), new_arcs, reporter=reporter
        )
        return results

    async def audit_producer_plan(self, genre: str, keywords: str, trend_memo: str) -> Optional[HegemonyAuditResult]:
        """PlanningAgent内でAIプロデューサー診断を実行"""
        prompt = self.engine.pm.build_producer_audit_prompt(genre, keywords, trend_memo)
        res = await self.engine._generate_json(MODEL_PLANNING, prompt, response_schema=HegemonyAuditResult, temp=0.4)
        if res.success:
            try:
                return HegemonyAuditResult.model_validate(res.metadata)
            except Exception:
                pass
        return None

class WritingAgent:
    """本文執筆とパイプライン管理を担当"""
    def __init__(self, engine: "UltimateHegemonyEngine"):
        self.engine = engine

    async def generate_episodes(
        self, book_id: int, start_ep: int, end_ep: int, passion: float, target_word_count: int,
        do_refine: bool, reporter=None, env_state: Optional[Dict[str, str]] = None,
        is_easy_mode: bool = False
    ) -> int:
        book   = await self.engine.repo.get_book(book_id)
        char_db_models = await self.engine.repo.get_all_characters(book_id)
        # DBモデルを、属性アクセスが可能な Registry オブジェクトに変換
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
        genre_str      = book.genre if book and book.genre else "ファンタジー"

        is_light = is_light_style(style_key, genre_str)

        self.engine.current_ep_num = 0

        # 改善案1: 研磨指針を最初からシステム指示に統合
        refine_direction = STYLE_REFINEMENT_DIRECTIONS["light" if is_light else "heavy"]
        commercial_inst = f"\n【商用執筆プロトコル】\n{refine_direction}\n- 文字数の水増しではなく『描写の解像度』で目標を達成せよ。\n- 読者の興味を引く『フック』を各シーンの終わりに配置せよ。"

        integrity_monitor = PlotIntegrityMonitor(self.engine)
        logic_validator = InternalLogicValidator(self.engine)

        from backend.engine_prompts import get_rule_set
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

            from backend.engine_narrative import PacingGraph
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
                season=(env_state or {}).get("season", "春"),
                weather=(env_state or {}).get("weather", "晴天"),
            )

            script_text = plot.script_content or ""
            p_dump      = plot.model_dump()

            if reporter:
                reporter.report(f"👑 第{ep_num}話 [ストレス:{current_stress_for_episode}]: 最新コンテキストで執筆開始", "info")

            # --- 改善案9: Style RAG による文体サンプル注入 ---
            style_rag = StyleRagManager(self.engine)
            # シーン設計図を元に、最も「質感」が近いサンプルを検索
            hegemony_sample_text = await style_rag.find_best_sample(
                plot.detailed_blueprint,
                phase=plot.current_chain_phase,
                tag_hint=plot.catharsis_type if plot.is_catharsis else None
            )
            hegemony_inst = style_rag.format_as_prompt(hegemony_sample_text)

            current_target_word_count = target_word_count
            if is_important_ep:
                current_target_word_count = int(target_word_count * 1.5)

            # 自己最適化パッチの読み込み
            from config import GlobalConfig
            optimized_patch = GlobalConfig().get("optimized_prompt_patch", "")
            if optimized_patch:
                plot.lite_model_director_notes = (plot.lite_model_director_notes or "") + f"\n【自己最適化指示】: {optimized_patch}"

            # システム指示（執筆エンジンの人格と制約）の構築
            # キャラクターの癖 (ExpansionHooks) を初回執筆から反映させる
            char_hooks_list = []
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
                    char_hooks_list.append(f"■ {c.name}の描写フック: {', '.join(hooks)}")
            hooks_inst = "\n".join(char_hooks_list)

            sys_inst = (
                f"{style_inst}\n{rule_set_content}\n{commercial_inst}\n"
                f"【作品設定・描写フック】: {settings_ctx}\n{hooks_inst}\n"
                "【AI定型句の禁止】: 蹂躙、驚愕、絶望、静寂、圧倒、歓喜を禁じ、具体的肉体反応で描写せよ。\n"
                "【説明語りの禁止】: 地の文や台詞での長々とした設定説明を避け、行動や情景を通じて情報を伝えること（Show, don't tell）。\n"
                "【可読性の向上】: スマホ閲覧を前提とし、1段落は1〜3文程度に抑えること。\n"
                "【会話の比率】: Web小説のテンポを維持するため、会話文の比率を40〜50%に保つこと。\n"
                "【凄さの間接描写】: 主人公の活躍は、周囲の具体的反応（声の震え、後ずさり等）を用いて間接的に伝えよ。\n"
                "【引きの美学】: 最後は短い倒置法や体言止めを用い、次を読みたくなる『引き』で締めること。"
            )

            fw_prompt = self.engine.pm.build_final_writing_prompt(
                ep_num=ep_num,
                plot_data=p_dump,
                script_text=script_text,
                target_word_count=current_target_word_count,
                plot_thought_process=plot.thought_process,
                prose_sample=prev_prose,
                settings_ctx=bible_settings, # Dict形式で渡す
                char_static_ctx=static_ctx, char_dynamic_ctx=dynamic_ctx, prev_ctx=prev_ctx,
                is_climax=is_important_ep,
                pacing_inst=pacing.get("instruction", ""),
                villain_inst=villain_inst,
                director_notes=(plot.lite_model_director_notes or "") + hegemony_inst,
            )
            fw_prompt += f"\n{atmo_prompt}"
            if plot.lite_model_director_notes:
                fw_prompt += f"\n【⚠️ プロット時の自己批判・修正指示】\n{plot.lite_model_director_notes}"
            if phase_instruction:
                fw_prompt += phase_instruction

            # --- 執筆・監視ループ (Regeneration Process) ---
            max_retries = 1 if is_easy_mode else 2
            final_content = ""
            final_meta = {}
            is_integrity_ok = True
            missing = []

            # 高速化微調整: ループ外で一度だけキーワードを抽出（CPUコスト削減）
            blueprint_keywords = integrity_monitor.extract_keywords(plot.detailed_blueprint)

            for attempt in range(max_retries):
                # 1回目は精度重視、2回目は多様性を上げて突破を図る
                temp = 0.7 + (passion - 0.5) * 0.2 + (attempt * 0.15)
                final_res = await self.engine._generate_json(MODEL_WRITING, fw_prompt, system_instruction=sys_inst, temp=temp)
                final_meta, raw_content = final_res.unwrap_or({}, "")
                # Ensure metadata is normalized to a dict-like structure
                final_meta = OutputSanitizer.normalize_metadata(final_meta)

                # 高速なRegExベースの整合性チェック
                is_integrity_ok, rate, missing = await integrity_monitor.check_integrity(blueprint_keywords, plot.detailed_blueprint, raw_content)

                if is_easy_mode:
                    # かんたんモード: リトライせず1回で確定させ、不備は後続の加筆ステップへ回す
                    final_content = self.engine.formatter.format_for_kakuyomu(raw_content)
                    break

                if is_integrity_ok:
                    # 通常回では論理検証をスキップし、重要回（Payoff/Climax）のみ追加検証
                    if is_important_ep and plot.misunderstanding_gap:
                        is_logic_ok, missing_steps = await logic_validator.validate_misunderstanding_flow(raw_content, plot.misunderstanding_gap)
                        if not is_logic_ok:
                            if reporter: reporter.report(f"🚨 論理矛盾検知 (Attempt {attempt+1}): {missing_steps}。再試行します。", "warning")
                            continue

                    final_content = self.engine.formatter.format_for_kakuyomu(raw_content)
                    break
                else:
                    reason = f"整合性率 {rate*100:.0f}% (欠落: {', '.join(missing[:3])})"
                    if reporter:
                        reporter.report(f"🚨 整合性エラーを検知 (Attempt {attempt+1}): {reason}。強制再生成を実行します。", "warning")
                    if attempt == max_retries - 1:
                        final_content = self.engine.formatter.format_for_kakuyomu(raw_content) # 最終リトライ失敗

            # 文字数不足または整合性不備時の自動肉付け・修正ロジック (かんたんモード統合)
            content_len = len(final_content)
            should_amplify = content_len > 100 and content_len < current_target_word_count * 0.85
            should_fix = is_easy_mode and not is_integrity_ok and content_len > 100

            if should_amplify or should_fix:
                if reporter:
                    msg = "⚠️ 描写不足・整合性を一括補正中..." if should_fix else "⚠️ 文字数不足。描写を拡張中..."
                    reporter.report(msg, "warning")

                # 改善: 欠落要素の補正と同時に、キャラクター固有の「癖(ExpansionHooks)」を反映
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
                        char_hooks.append(f"■ {c.name}: {', '.join(hooks)}")
                hooks_inst = "\n【キャラクター固有の描写フック（必ず反映）】\n" + "\n".join(char_hooks) if char_hooks else ""

                fix_inst = f"\n【重要：以下の欠落要素を必ず含めて自然に加筆せよ】: {', '.join(missing)}" if should_fix and missing else ""
                amplify_prompt = self.engine.pm.build_amplify_prompt(final_content, current_target_word_count, fix_inst + hooks_inst)

                res_amp = await self.engine._generate_json(MODEL_WRITING, amplify_prompt, temp=0.85)
                _, amp_content = res_amp.unwrap_or({}, final_content)
                final_content = self.engine.formatter.format_for_kakuyomu(amp_content)

            # 有機的結合: DB設定に基づき、キャラクターの口調・人称を最終強制補正
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
                    reporter.report("📏 リズム単調さを検知。自動補正を実行します...", "warning")
                original_before_rhythm = final_content
                final_content = ContentValidator.auto_correct_rhythm(final_content)
                tone_errors   = verify_character_tone(original_before_rhythm, final_content)
                for err in tone_errors:
                    if reporter:
                        reporter.report(err, "warning")

            # 改善案3: Payoffフェーズまたは重要回のみ厳密な監査を行う（それ以外はスキップして高速化）
            should_deep_audit = is_important_ep or plot.current_chain_phase == "Payoff"
            if reporter and should_deep_audit:
                reporter.report(f"🔍 第{ep_num}話 物語の整合性をチェック中...", "info")

            f_audit = await self.engine.auditor.audit_foreshadowing_payoff(book_id, ep_num, final_content) if should_deep_audit else ForeshadowingAudit(is_recovered=True)
            audit_log_data = {}

            if should_deep_audit:
                if not f_audit.is_recovered and f_audit.missing_items:
                    # 改善案3: 自動リトライ（書き直し）を廃止し、ユーザーへの警告のみにする
                    reporter.report(f"⚠️ 伏線未回収を検知しました。プロット設計図を確認してください: {', '.join(f_audit.missing_items)}", "warning")
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
                        reporter.report(f"⚠️ 軽量監査警告: {conflict}", "warning")
                audit_log_data = light_audit.model_dump()
                audit_log_data = OutputSanitizer.normalize_metadata(audit_log_data)

            total_len += len(final_content)

            stress_delta = int(final_meta.get("stress_delta", 0) / 10)
            current_stress = max(0, current_stress_for_episode + stress_delta)
            await self.engine.repo.update_book_cumulative_stress(book_id, current_stress)

            if reporter:
                reporter.update_progress(
                    ep_num - start_ep + 1, end_ep - start_ep + 1,
                    f"第{ep_num}話 完了 ({len(final_content)}文字) [ストレス→{current_stress}]"
                )

            await self.engine.repo.create_chapter(
                book_id, ep_num,
                p_dump.get("title", f"第{ep_num}話"),
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
        # キューサイズを広げ、先行してプロットを作れるようにする
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
            # プロットと執筆済みチャプターをスキャンして修復が必要なものを特定
            existing_plots = await self.engine.repo.get_plots_between(book_id, start_ep, end_ep)
            chapters = await self.engine.repo.get_all_non_anchor_chapters(book_id)
            chap_nums = {c.ep_num for c in chapters}

            plots_to_generate = []
            for ep in range(start_ep, end_ep + 1):
                if ep in chap_nums:
                    continue # 既に本文がある場合はスキップ

                # チャプターがない場合、既存プロットの有無を確認
                plot = next((p for p in existing_plots if p.ep_num == ep), None)
                if plot and plot.detailed_blueprint and len(plot.detailed_blueprint) > 100:
                    # プロットがあるなら即座に執筆キューへ
                    await plot_queue.put(plot)
                    if reporter: reporter.report(f"📂 既存プロットを利用: 第{ep}話", "info")
                else:
                    # プロットもないなら生成対象へ
                    plots_to_generate.append(ep)

            # プロット生成自体を並行タスクとして管理する
            plot_tasks = []
            try:
                async def _produce_plot(ep_num):
                    if stop_event.is_set(): return
                    if reporter: reporter.report(f"🗺️ プロット生成中: 第{ep_num}話", "info")
                    try:
                        p_res = await self.engine.planner.expand_plots(book_id, [ep_num], arcs, reporter=reporter, force=False)
                        if p_res:
                            if p_res[0].get("status") == "failed_plot_gen": # Check for failure indicator
                                failed_plot_generations.append(p_res[0])
                                if reporter: reporter.report(f"⚠️ プロット生成失敗: 第{ep_num}話 ({p_res[0]['error_message']})", "warning")
                            else:
                                await plot_queue.put(p_res[0])
                                if reporter: reporter.report(f"✅ プロット生成完了: 第{ep_num}話", "info")
                    except asyncio.CancelledError:
                        logger.info(f"Plot generation for ep {ep_num} was cancelled.")
                        failed_plot_generations.append({"ep_num": ep_num, "status": "cancelled", "error_message": "Plot generation cancelled."})
                    except Exception as e:
                        logger.error(f"Error producing plot for ep {ep_num}: {e}")
                        failed_plot_generations.append({"ep_num": ep_num, "status": "failed_plot_gen", "error_message": str(e)})

                # すべての話数のプロット生成を並行して開始（内部でSemaphore(4)が効く）
                tasks = [asyncio.create_task(_produce_plot(ep)) for ep in plots_to_generate]
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
                        if reporter: reporter.report(f"⚠️ 第{item['ep_num']}話の執筆をスキップ (プロット生成失敗)", "warning")
                        plot_queue.task_done()
                        continue
                    elif isinstance(item, Exception): # If a raw exception somehow gets through
                        failed_episodes.append({"ep_num": "Unknown", "status": "critical_error", "error_message": str(item)})
                        if reporter: reporter.report(f"🚨 パイプラインで予期せぬエラーが発生: {item}", "error")
                        stop_event.set() # Stop the pipeline on critical unhandled exception
                        continue

                    # ep_num を確実に取得
                    ep = item.get("ep_num") if isinstance(item, dict) else getattr(item, 'ep_num', None)
                    if ep is None: continue # Should not happen with proper plotter failure handling

                    if reporter: reporter.report(f"✍️ 本文執筆中: 第{ep}話", "info")
                    async with write_sem:
                        chars_count = await self.generate_episodes(book_id, ep, ep, passion, target_word_count, True, reporter, is_easy_mode=is_easy_mode)
                        total_chars[0] += chars_count
                    plot_queue.task_done()
            except Exception as e:
                logger.error(f"Writer Error at ep {ep if 'ep' in locals() else 'unknown'}: {e}")
                failed_episodes.append({"ep_num": ep, "status": "failed_writing", "error_message": str(e)})
                if is_easy_mode:
                    if reporter: reporter.report(f"⚠️ 第{ep}話の執筆中にエラーが発生しましたが、続行します。", "warning")
                    # キューの状態を正常化して続行
                    try: plot_queue.task_done()
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
                return {"error": "作品が見つかりません"}
            plot  = await self.engine.repo.get_plot(book_id, ep_num)
            prompt = self.engine.pm.build_analyze_import_chapter_prompt(cleaned_content, EpisodeDraft)
            res = await self.engine._generate_json(MODEL_PLANNING, prompt, response_schema=EpisodeDraft)
            if res.success:
                data = res.metadata
                # 保存処理
                await self.engine.repo.create_chapter(
                    book_id, ep_num, data.get("title", f"第{ep_num}話"),
                    cleaned_content, data.get("summary", ""),
                    None, "Imported", data.get("next_world_state", {}),
                    {"note": "Imported via analyze_and_import_chapter"},
                    time.strftime('%Y-%m-%dT%H:%M:%S')
                )
                return data
            return {"error": "分析に失敗しました"}
        except Exception as e:
            return {"error": str(e)}

