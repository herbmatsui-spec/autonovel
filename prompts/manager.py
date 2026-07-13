from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from jinja2 import Environment

from config import BASE_DIR
from prompts.plotting import EMOTIONAL_HOOK_TEMPLATE
from prompts.registry import PromptRegistry

logger = logging.getLogger(__name__)

class PromptManager:
    """
    プロンプトテンプレートの管理およびレンダリングを行うマネージャー。
    PromptRegistry を通じて、ファイルシステムおよびDBベースのプロンプトを解決する。
    """

    def __init__(self, prompts_dir: Union[str, Environment] = "prompts", jinja_env: Optional[Environment] = None):
        # テストフィクスチャなどで jinja_env が第一引数に渡されるケースへの対応
        if isinstance(prompts_dir, Environment):
            actual_prompts_dir = "prompts"
            actual_jinja_env = prompts_dir
        else:
            actual_prompts_dir = prompts_dir
            actual_jinja_env = jinja_env

        # プロンプトディレクトリの絶対パスを設定
        self.prompts_path = BASE_DIR / actual_prompts_dir

        # Registry の初期化 (DBマネージャーなどは必要に応じて外部から注入される)
        self.registry = PromptRegistry(templates_dir=str(self.prompts_path))

        # jinja_env が提供されている場合は registry に適用する（registry側でサポートされている前提）
        if actual_jinja_env:
            if hasattr(self.registry, 'jinja_env'):
                self.registry.jinja_env = actual_jinja_env

        logger.info(f"PromptManager initialized with registry path: {self.prompts_path}")

    async def render_async(self, template_name: str, *args: Any, **kwargs: Any) -> str:
        """
        テンプレートを非同期にレンダリングしてプロンプト文字列を返す。
        DB上のオーバーライドがある場合はそれを優先的に適用する。
        """
        book_id = kwargs.pop("book_id", None)
        context = {}
        if args:
            if isinstance(args[0], dict):
                context.update(args[0])
            elif isinstance(args[0], int) or args[0] is None:
                book_id = args[0]
        context.update(kwargs)
        return await self.registry.render_async(template_name, context, book_id=book_id)


    async def build_producer_audit_prompt(self, genre: str, keywords: str, trend_memo: str, book_id: Optional[int] = None) -> str:
        available_tropes = [
            "ざまぁ", "断罪", "成り上がり", "無自覚無双", "圧倒的報復", "追放ざまぁ",
            "ヤンデレヒロイン", "実は有能な従者", "狂信的な配下", "不遇な天才", "共依存",
            "戦わない最強", "復讐しない追放者", "善人すぎる悪役",
        ]
        tropes_text = f"【選択可能な要素リスト】: {', '.join(available_tropes)}" if available_tropes else ""

        return await self.render_async(
            "ai_producer_audit.j2",
            {
                "genre": genre,
                "keywords": keywords,
                "trend_memo": trend_memo,
                "available_tropes": tropes_text
            },
            book_id=book_id
        )

    async def build_plot_integrity_audit_prompt(self, synopsis: str, world_settings_json: str, schema_json: Any, book_id: Optional[int] = None, **kwargs: Any) -> str:
        return await self.render_async(
            "plot_integrity_audit_prompt.j2",
            {
                "synopsis": synopsis,
                "world_settings_json": world_settings_json,
                "schema_json": schema_json,
                **kwargs
            },
            book_id=book_id
        )

    async def build_logical_audit_prompt(self, past_facts: str, plot_bp: str, script: str, book_id: Optional[int] = None) -> str:
        return await self.render_async(
            "logical_audit.j2",
            {
                "past_facts": past_facts,
                "plot_bp": plot_bp,
                "script": script
            },
            book_id=book_id
        )

    async def build_foreshadowing_audit_prompt(self, f_map: List[Dict[str, Any]], content: str, book_id: Optional[int] = None) -> str:
        import json
        return await self.render_async(
            "foreshadowing_audit.j2",
            {
                "f_map_json": json.dumps(f_map, ensure_ascii=False),
                "content": content[:4000]
            },
            book_id=book_id
        )

    async def build_narrative_scoring_prompt(self, scene_content: str, context: str, previous_metrics: Optional[str] = None, book_id: Optional[int] = None) -> str:
        """
        物語の指標スコアリング用のプロンプトを構築する。
        """
        return await self.render_async(
            "narrative_scoring_prompt.j2",
            {
                "scene": scene_content,
                "context": context,
                "previous_metrics": previous_metrics or "None",
            },
            book_id=book_id
        )

    async def build_tension_audit_prompt(self, curve_str: str, book_id: Optional[int] = None) -> str:
        return await self.render_async(
            "tension_audit_prompt.j2",
            {
                "curve_str": curve_str
            },
            book_id=book_id
        )

    async def build_tension_adjustment_prompt(self, ep_num: int, current_tension: int, action: str, reason: str, book_id: Optional[int] = None) -> str:
        return await self.render_async(
            "tension_adjustment_prompt.j2",
            {
                "ep_num": ep_num,
                "current_tension": current_tension,
                "action": action,
                "reason": reason
            },
            book_id=book_id
        )

    async def build_marketing_pack_prompt(self, book_title: str, synopsis: str, latest_ep: int, book_id: Optional[int] = None) -> str:
        return await self.render_async(
            "marketing_pack_prompt.j2",
            {
                "book_title": book_title,
                "synopsis": synopsis,
                "latest_ep": latest_ep
            },
            book_id=book_id
        )

    async def build_title_generation_prompt(self, genre: str, keywords: str, book_id: Optional[int] = None) -> str:
        return await self.render_async(
            "title_generation_prompt.j2",
            {
                "genre": genre,
                "keywords": keywords
            },
            book_id=book_id
        )

    async def build_style_dna_analysis_prompt(self, sample_text: str, book_id: Optional[int] = None) -> str:
        return await self.render_async(
            "style_dna_analysis_prompt.j2",
            {
                "sample_text": sample_text[:3000]
            },
            book_id=book_id
        )

    async def build_world_creation_prompt(self, genre: str, keywords: str, response_schema: Any, book_id: Optional[int] = None, **kwargs: Any) -> str:
        return await self.render_async(
            "world_creation_prompt.j2",
            {
                "genre": genre,
                "keywords": keywords,
                "schema_json": response_schema.model_json_schema() if hasattr(response_schema, 'model_json_schema') else response_schema,
                **kwargs
            },
            book_id=book_id
        )

    async def build_mc_creation_prompt(self, world_rules_json: str, genre: str, keywords: str, concept: str = "", book_id: Optional[int] = None, **kwargs: Any) -> str:
        return await self.render_async(
            "mc_creation_prompt.j2",
            {
                "genre": genre,
                "keywords": keywords,
                "concept": concept,
                "world_rules_json": world_rules_json,
                **kwargs
            },
            book_id=book_id
        )

    async def build_foreshadowing_extraction_prompt(self, plot_text: str, ep_num: int, book_id: Optional[int] = None) -> str:
        return await self.render_async(
            "foreshadowing_extraction.j2",
            {
                "plot_text": plot_text,
                "ep_num": ep_num
            },
            book_id=book_id
        )

    async def build_character_arc_extraction_prompt(self, plot_text: str, ep_num: int, book_id: Optional[int] = None) -> str:
        return await self.render_async(
            "character_arc_extraction.j2",
            {
                "plot_text": plot_text,
                "ep_num": ep_num
            },
            book_id=book_id
        )

    # 互換性維持のためのダミーメソッド（将来的に削除またはテンプレート化）
    def get_style_instruction(self, style_key: str, book_id: Optional[int] = None) -> str:
        # TODO: テンプレート化
        return ""

    async def build_global_repair_prompt(self, conflict_report: str, synopsis: str, world_rules: str, mc_profile: str, book_id: Optional[int] = None, **kwargs: Any) -> str:
        return await self.render_async(
            "global_repair_prompt.j2",
            {
                "conflict_report": conflict_report,
                "synopsis": synopsis,
                "world_rules": world_rules,
                "mc_profile": mc_profile,
                **kwargs
            },
            book_id=book_id
        )

    async def build_fast_plot_screen_prompt(self, blueprint: str, book_id: Optional[int] = None) -> str:
        return await self.render_async(
            "fast_plot_screen_prompt.j2",
            {
                "blueprint": blueprint
            },
            book_id=book_id
        )

    async def build_ability_audit_prompt(self, blueprint: str, settings_json: str, characters_json: str, book_id: Optional[int] = None) -> str:
        return await self.render_async(
            "ability_audit_prompt.j2",
            {
                "blueprint": blueprint,
                "settings_json": settings_json,
                "characters_json": characters_json
            },
            book_id=book_id
        )

    async def build_deai_audit_prompt(self, content: str, book_id: Optional[int] = None) -> str:
        return await self.render_async(
            "deai_audit_prompt.j2",
            {
                "content": content[:4000]
            },
            book_id=book_id
        )

    async def build_deai_propose_rules_prompt(self, content: str, domain: str, book_id: Optional[int] = None) -> str:
        return await self.render_async(
            "deai_propose_rules_prompt.j2",
            {
                "content": content[:4000],
                "domain": domain
            },
            book_id=book_id
        )

    async def build_apc_system_prompt(self, style_key: str, write_rule_type: str, settings_ctx_json: str, hooks_inst: str, char_static_ctx: str, book_id: Optional[int] = None) -> str:
        style_inst = await self.build_style_instruction(style_key, book_id=book_id)
        from config.styles import get_rule_set
        rule_set_content = get_rule_set(write_rule_type)

        # logic for direction
        # simplified direction logic or delegate to a template
        direction = "heavy" # Default or calculate based on style_key
        if "light" in style_key or "short" in style_key:
            direction = "light"

        commercial_inst = await self.render_async("commercial_protocol.j2", direction=direction, book_id=book_id)
        hook_inst = await self._build_hook_strategy_section(book_id=book_id)

        return await self.render_async(
            "apc_system.j2",
            book_id=book_id,
            style_inst=style_inst,
            rule_set_content=rule_set_content,
            commercial_inst=commercial_inst,
            settings_ctx_json=settings_ctx_json,
            hooks_inst=hooks_inst,
            char_static_ctx=char_static_ctx,
            hook_inst=hook_inst
        )

    async def build_beat_mapping_prompt(self, final_content: str, beats: List[str], book_id: Optional[int] = None) -> str:
        import json
        return await self.render_async(
            "beat_mapping_prompt.j2",
            book_id=book_id,
            beats_json=json.dumps(beats, ensure_ascii=False, indent=2),
            final_content=final_content
        )

    async def build_delta_polish_prompt(self, target_beat: str, target_word_count: int, prefix_text: str, suffix_text: str, instructions: str, book_id: Optional[int] = None) -> str:
        return await self.render_async(
            "delta_polish_prompt.j2",
            book_id=book_id,
            target_beat=target_beat,
            target_word_count=target_word_count,
            prefix_text=prefix_text,
            suffix_text=suffix_text,
            instructions=instructions
        )

    async def build_fw_prompt_from_structured_context(self, title: str, ep_num: int, context_data: Any, blueprint: str, book_id: Optional[int] = None, extra_instruction: str = "") -> str:
        static_ctx_lines = [f"■ {k}: {v}" for k, v in context_data.immutable.static_character_profiles.items()]
        dyn_ctx_lines = [f"■ {k}: {v}" for k, v in context_data.dynamic.character_states.items()]

        static_ctx = "\n".join(static_ctx_lines)
        dyn_ctx = "\n".join(dyn_ctx_lines)
        prev_ctx = context_data.immutable.past_summary

        constraints = ""
        if context_data.config.active_constraints:
            constraints = "【世界制約】\n" + "\n".join([f"- {c.get('constraint', '')}" for c in context_data.config.active_constraints]) + "\n\n"

        return await self.render_async(
            "writing_context_prompt.j2",
            book_id=book_id,
            title=title,
            ep_num=ep_num,
            extra_instruction=extra_instruction,
            constraints=constraints,
            prev_ctx=prev_ctx,
            static_ctx=static_ctx,
            dyn_ctx=dyn_ctx,
            blueprint=blueprint
        )

    async def build_dry_run_prompt(self, ep_num: int, improved_prompt: str, plot_detailed_blueprint: str, plot_script_content: str, book_id: Optional[int] = None) -> str:
        return await self.render_async(
            "dry_run_prompt.j2",
            book_id=book_id,
            ep_num=ep_num,
            improved_prompt=improved_prompt,
            plot_detailed_blueprint=plot_detailed_blueprint,
            plot_script_content=plot_script_content
        )

    async def build_polishing_prompt(self, draft_content: str, target_word_count: int, style_key: str, prose_sample: str, plot_data: Optional[Dict[str, Any]] = None, use_beat_rules: bool = True, book_id: Optional[int] = None, **kwargs) -> str:
        forbidden_inst = await self._build_forbidden_section(book_id=book_id)
        hook_inst = await self._build_hook_strategy_section(book_id=book_id)

        specialized_rules_data = []
        if use_beat_rules and plot_data:
            scenes = plot_data.get("scenes", [])
            for i, scene in enumerate(scenes):
                action = scene.get("action", "") if isinstance(scene, dict) else str(scene)
                specialized_rules_data.append({"scene_no": i + 1, "action": action})

        return await self.render_async(
            "polishing.j2",
            {
                "specialized_rules_data": specialized_rules_data,
                "forbidden_inst": forbidden_inst,
                "hook_inst": hook_inst,
                "style_sample": prose_sample,
                "target_word_count": target_word_count,
                "draft_content": draft_content,
                **kwargs
            },
            book_id=book_id
        )

    async def build_critic_feedback_prompt(self, issue_list: Any, draft_content: str, blueprint: str, book_id: Optional[int] = None) -> str:
        import json

        from src.models.audit import CriticFeedback
        issues_json = ""
        if hasattr(issue_list, "model_dump_json"):
            issues_json = issue_list.model_dump_json(indent=2)
        elif hasattr(issue_list, "dict"):
            issues_json = json.dumps(issue_list.dict(), ensure_ascii=False, indent=2)
        else:
            issues_json = str(issue_list)

        return await self.render_async(
            "critic_feedback.j2",
            {
                "issues_json": issues_json,
                "blueprint": blueprint,
                "draft_content": draft_content,
                "schema_json": json.dumps(CriticFeedback.model_json_schema(), ensure_ascii=False, indent=2)
            },
            book_id=book_id
        )

    async def build_fw_prompt(self, title: str, ep_num: int, static_ctx: str, dyn_ctx: str, prev_ctx: str, blueprint: str, book_id: Optional[int] = None, extra_instruction: str = "") -> str:
        return await self.render_async(
            "writing_context_prompt.j2",
            {
                "title": title,
                "ep_num": ep_num,
                "static_ctx": static_ctx,
                "dyn_ctx": dyn_ctx,
                "prev_ctx": prev_ctx,
                "blueprint": blueprint,
                "extra_instruction": extra_instruction
            },
            book_id=book_id
        )

    async def build_drafting_prompt(self, ep_num: int, plot_data: Dict[str, Any], script_text: str, target_word_count: int,
                                    char_static_ctx: str, char_dynamic_ctx: str, prev_ctx: str, book_id: Optional[int] = None, **kwargs) -> Tuple[str, str]:
        scenes_data = plot_data.get("scenes", [])
        quota_inst = await self._build_quota_section(scenes_data, target_word_count, book_id=book_id)
        show_tell_inst = await self._build_show_tell_section(scenes_data, book_id=book_id)

        settings_ctx = kwargs.get('settings_ctx', '{}')
        if isinstance(settings_ctx, str):
            import json
            try:
                settings_ctx = json.loads(settings_ctx)
            except:
                settings_ctx = {}
        if not isinstance(settings_ctx, dict):
            settings_ctx = {}

        assertion_inst = await self._build_assertion_section(settings_ctx.get('active_constraints', []), book_id=book_id)

        phase = plot_data.get("current_chain_phase", "Hate")
        tone_inst = await self.render_async("tone_instruction.j2", {"phase": phase}, book_id=book_id)

        style_key = kwargs.get("style_key", "style_web_standard")
        write_rule_type = kwargs.get("write_rule_type", "RULE_SET_A")
        style_inst = await self.build_style_instruction(style_key, book_id=book_id)

        from config.styles import get_rule_set
        rule_set_content = get_rule_set(write_rule_type)

        sys_inst = await self.render_async(
            "drafting_system.j2",
            {
                "style_inst": style_inst,
                "rule_set_content": rule_set_content,
                "specialized_amp_inst": "",
            },
            book_id=book_id
        )

        # ダイバージェンス指示のレンダリング（divergence_type_name が kwargs にある場合）
        divergence_type_name = kwargs.get("divergence_type_name", "safe")
        div_inst = await self.render_async("writing_divergence.j2", {"divergence_type_name": divergence_type_name}, book_id=book_id)

        user_prompt = await self.render_async(
            "drafting_user.j2",
            {
                "quota_inst": quota_inst,
                "show_tell_inst": show_tell_inst,
                "assertion_inst": assertion_inst,
                "char_static_ctx": char_static_ctx,
                "char_dynamic_ctx": char_dynamic_ctx,
                "prev_ctx": prev_ctx,
                "script_text": script_text,
                "blueprint": plot_data.get('detailed_blueprint', ''),
                "target_word_count": target_word_count,
                "divergence_instruction": div_inst,
                "tone_inst": tone_inst,
                "director_notes": kwargs.get('director_notes'),
            },
            book_id=book_id
        )
        return sys_inst, user_prompt

    async def build_rebuild_plot_outline_prompt(self, book_title: str, start_ep: int, new_total_eps: int, book_synopsis: str, keywords: str, trend_memo: str, pending_foreshadowing: List[str], book_id: Optional[int] = None, **kwargs: Any) -> str:
        return await self.render_async(
            "rebuild_plot_outline_prompt.j2",
            {
                "book_title": book_title,
                "start_ep": start_ep,
                "new_total_eps": new_total_eps,
                "book_synopsis": book_synopsis,
                "keywords": keywords,
                "trend_memo": trend_memo,
                "pending_foreshadowing": pending_foreshadowing,
                **kwargs
            },
            book_id=book_id
        )

    async def build_amplify_prompt(self, final_content: str, current_target_word_count: int, fix_inst: str = "", book_id: Optional[int] = None) -> str:
        return await self.render_async(
            "amplify_prompt.j2",
            {
                "final_content": final_content,
                "current_target_word_count": current_target_word_count,
                "fix_inst": fix_inst
            },
            book_id=book_id
        )

    async def build_analyze_import_chapter_prompt(self, cleaned_content: str, episode_draft_schema: Any, book_id: Optional[int] = None) -> str:
        return await self.render_async(
            "analyze_import_chapter_prompt.j2",
            {
                "cleaned_content": cleaned_content[:5000],
                "schema_json": episode_draft_schema.model_json_schema() if hasattr(episode_draft_schema, 'model_json_schema') else episode_draft_schema
            },
            book_id=book_id
        )

    async def build_critique_quality_prompt(self, book_title: str, summary_data_json: str, book_id: Optional[int] = None) -> str:
        return await self.render_async(
            "critique_quality.j2",
            {
                "book_title": book_title,
                "summary_data_json": summary_data_json
            },
            book_id=book_id
        )

    async def build_iterative_gap_analysis_prompt(self, book_genre: str, book_title: str, batch_data: str, book_id: Optional[int] = None) -> str:
        return await self.render_async(
            "iterative_gap_analysis.j2",
            {
                "book_genre": book_genre,
                "book_title": book_title,
                "batch_data": batch_data
            },
            book_id=book_id
        )

    async def build_plot_expansion_prompt(self, book_title: str, ep_num: int, ep_info: Any, past_plots: List[Any], arcs: List[Any], book_genre: str, book_id: Optional[int] = None, emotional_hook: Optional[Any] = None, **kwargs: Any) -> str:
        def safe_dict(obj: Any) -> Dict[str, Any]:
            if isinstance(obj, dict): return obj
            if hasattr(obj, 'model_dump') and callable(obj.model_dump): return obj.model_dump()
            if hasattr(obj, 'dict') and callable(obj.dict): return obj.dict()
            return {k: getattr(obj, k) for k in ['arc_num', 'title', 'start_ep', 'end_ep', 'one_line_summary', 'resolution_style', 'burned_cost_or_loot', 'thematic_milestone', 'antagonist_status'] if hasattr(obj, k)}

        def fmt_arc(a):
            d = safe_dict(a)
            return f"- Arc {d.get('arc_num', '?')}: {d.get('title', '無題')} (Ep {d.get('start_ep', '?')}-{d.get('end_ep', '?')})"

        past_plots_str = "\n".join([f"- 第{getattr(p, 'ep_num', '?')}話: {getattr(p, 'summary', '未定義')}" for p in past_plots]) if past_plots else "なし"
        arcs_str = "\n".join([fmt_arc(a) for a in arcs]) if arcs else "なし"
        ep_info_dict = safe_dict(ep_info)

        from src.models.plot import PlotEpisode

        # ダイバージェンス指示のレンダリング
        divergence_inst = await self.render_async("divergence_instruction.j2", {}, book_id=book_id)

        prompt = await self.render_async(
            "plot_expansion_prompt.j2",
            {
                "book_title": book_title,
                "book_genre": book_genre,
                "ep_num": ep_num,
                "one_line_summary": ep_info_dict.get('one_line_summary', '未定義'),
                "resolution_style": ep_info_dict.get('resolution_style', 'Cheat'),
                "burned_cost_or_loot": ep_info_dict.get('burned_cost_or_loot', 'なし'),
                "thematic_milestone": ep_info_dict.get('thematic_milestone', 'なし'),
                "antagonist_status": ep_info_dict.get('antagonist_status', '現状維持'),
                "past_plots_str": past_plots_str,
                "arcs_str": arcs_str,
                "divergence_instruction": divergence_inst,
                "schema_json": PlotEpisode.model_json_schema()
            },
            book_id=book_id
        )

        if emotional_hook is not None:
            hook_text = EMOTIONAL_HOOK_TEMPLATE.format(
                one_line_intent=getattr(emotional_hook, "one_line_intent", str(emotional_hook)),
                target_tension_peak=getattr(emotional_hook, "target_tension_peak", 80),
            )
            prompt = f"{prompt}\n\n{hook_text}"

        return prompt

    async def build_sharp_edge_proposal_prompt(self, plot_summary: str, book_id: Optional[int] = None) -> str:
        """
        プロット概要から「削ってはいけない3つの角」を提案させるプロンプトを生成する。
        """
        from prompts.plotting import SHARP_EDGE_PROPOSAL_TEMPLATE

        prompt = SHARP_EDGE_PROPOSAL_TEMPLATE.format(plot_summary=plot_summary)
        return prompt

    async def build_early_entertainment_check_prompt(self, rough_plot: str, opening_500_chars: str, book_id: Optional[int] = None) -> str:
        """
        早期面白さ検証用プロンプトを生成する。

        品質を評価せず、面白さのみを評価するようLLMに指示する。
        """
        from prompts.plotting import EARLY_ENTERTAINMENT_CHECK_TEMPLATE

        prompt = EARLY_ENTERTAINMENT_CHECK_TEMPLATE.format(
            rough_plot=rough_plot,
            opening_500_chars=opening_500_chars[:500],
        )
        return prompt

    async def build_sub_char_creation_prompt(self, world_rules_json: str, mc_data_json: str, causality_map: List[str], mc_name: str, book_id: Optional[int] = None, **kwargs: Any) -> str:
        import json

        from src.models.character import CharacterRegistry
        return await self.render_async(
            "sub_char_creation_prompt.j2",
            {
                "world_rules_json": world_rules_json,
                "mc_data_json": mc_data_json,
                "causality_map_json": json.dumps(causality_map, ensure_ascii=False),
                "mc_name": mc_name,
                "schema_json": CharacterRegistry.model_json_schema()
            },
            book_id=book_id
        )

    async def build_bible_creation_prompt(self, bible_core_schema: Any, world_rules_json: str, concept: str, target_eps: int, book_id: Optional[int] = None, **kwargs: Any) -> str:
        # engine_key == 'zamaa' の場合は、専用のざまぁバイブルテンプレートを使用する
        template_name = "bible_creation_prompt.j2"
        if kwargs.get("engine_key") == "zamaa":
            template_name = "bible_zamaa_template.j2"

        return await self.render_async(
            template_name,
            {
                "target_eps": target_eps,
                "world_rules_json": world_rules_json,
                "concept": concept,
                "schema_json": bible_core_schema.model_json_schema() if hasattr(bible_core_schema, 'model_json_schema') else bible_core_schema,
                **kwargs
            },
            book_id=book_id
        )

    async def build_marketing_ab_test_prompt(self, bible_core_concept: str, book_id: Optional[int] = None, **kwargs: Any) -> str:
        return await self.render_async(
            "marketing_ab_test_prompt.j2",
            {
                "bible_core_concept": bible_core_concept
            },
            book_id=book_id
        )

    async def build_roadmap_prompt(self, bible_core_title: str, bible_core_synopsis: str, target_eps: int, roadmap_list_schema: Any, book_id: Optional[int] = None, **kwargs: Any) -> str:
        return await self.render_async(
            "roadmap_prompt.j2",
            {
                "bible_core_title": bible_core_title,
                "bible_core_synopsis": bible_core_synopsis,
                "target_eps": target_eps,
                "schema_json": roadmap_list_schema.model_json_schema() if hasattr(roadmap_list_schema, 'model_json_schema') else roadmap_list_schema,
            },
            book_id=book_id
        )

    async def _build_quota_section(self, scenes_data: Any, target_word_count: int, book_id: Optional[int] = None) -> str:
        if isinstance(scenes_data, str):
            scenes_data = [{"action": scenes_data}]
        if not isinstance(scenes_data, list) or not scenes_data:
            return ""

        normalized_scenes = [s if isinstance(s, dict) else {"action": str(s)} for s in scenes_data]
        total_impact = sum(s.get('impact_score', 50) for s in normalized_scenes) or 1

        return await self.render_async(
            "quota_section.j2",
            book_id=book_id,
            normalized_scenes=normalized_scenes,
            target_word_count=target_word_count,
            total_impact=total_impact
        )

    async def _build_show_tell_section(self, scenes_data: Any, book_id: Optional[int] = None) -> str:
        if isinstance(scenes_data, str):
            scenes_data = [{"action": scenes_data}]
        if not isinstance(scenes_data, list) or not scenes_data:
            return ""

        normalized_scenes = [s if isinstance(s, dict) else {"action": str(s)} for s in scenes_data]
        return await self.render_async("show_tell_section.j2", book_id=book_id, normalized_scenes=normalized_scenes)

    async def _build_forbidden_section(self, book_id: Optional[int] = None) -> str:
        import random

        from config import FORBIDDEN_SUMMARY_PATTERNS, FORBIDDEN_WORD_REPLACEMENTS

        if not FORBIDDEN_WORD_REPLACEMENTS and not FORBIDDEN_SUMMARY_PATTERNS:
            return ""

        # 1. 通常の禁止語置換の抽出
        word_data = {}
        if FORBIDDEN_WORD_REPLACEMENTS:
            word = random.choice(list(FORBIDDEN_WORD_REPLACEMENTS.keys()))
            word_data = {
                "forbidden_word": word,
                "replacement_word": FORBIDDEN_WORD_REPLACEMENTS[word]
            }

        # 2. あらすじ的記述禁止パターンの抽出
        summary_data = {}
        if FORBIDDEN_SUMMARY_PATTERNS:
            pattern = random.choice(list(FORBIDDEN_SUMMARY_PATTERNS.keys()))
            summary_data = {
                "summary_forbidden_pattern": pattern,
                "summary_replacement_instruction": FORBIDDEN_SUMMARY_PATTERNS[pattern]
            }

        return await self.render_async(
            "forbidden_section.j2",
            book_id=book_id,
            **word_data,
            **summary_data
        )

    async def _build_hook_strategy_section(self, book_id: Optional[int] = None) -> str:
        return await self.render_async("hook_strategy_section.j2", book_id=book_id)

    async def _build_assertion_section(self, constraints: List[Any], book_id: Optional[int] = None) -> str:
        if not constraints:
            return ""
        return await self.render_async("assertion_section.j2", book_id=book_id, constraints=constraints)

    async def build_style_instruction(self, style_key: str, book_id: Optional[int] = None) -> str:
        return await self.render_async("style_instruction.j2", book_id=book_id, style_key=style_key)

    async def build_bible_extraction_prompt(self, content: str, book_id: Optional[int] = None) -> str:
        return await self.render_async("bible_extraction.j2", book_id=book_id, content=content)

    async def get_villain_instruction(self, genre: str, book_id: Optional[int] = None) -> str:
        from src.core.plugin_loader import PluginLoader
        plugin = PluginLoader.get_instance().get_active_plugin()
        strategies = getattr(plugin, 'villain_strategies', {})

        selected_strategy = strategies.get("default", "敵対者は知略的であり、主人公を精神的に追い詰める戦略を採れ。")
        for key, strategy in strategies.items():
            if key in genre:
                selected_strategy = strategy
                break

        return await self.render_async(
            "villain_instruction.j2",
            book_id=book_id,
            strategy=selected_strategy,
            genre=genre
        )

    async def build_refinement_prompt(self, content: str, style_key: str, is_light: bool, target_word_count: int, book_id: Optional[int] = None) -> str:
        return await self.render_async("refinement_prompt.j2", book_id=book_id, content=content, style_key=style_key, is_light=is_light, target_word_count=target_word_count)

# シングルトンインスタンスを提供
prompt_manager = PromptManager()

