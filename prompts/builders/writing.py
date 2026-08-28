from __future__ import annotations

import json
import logging

from typing import Any, List, Optional, Tuple
from jinja2 import Environment

from prompts.registry import PromptRegistry
from prompts.schemas import WritingContext

logger = logging.getLogger(__name__)


class WritingPromptBuilder:
    """執筆系プロンプト（下書き、最終執筆、磨き等）を構築するビルダー。"""

    def __init__(self, registry: PromptRegistry, jinja_env: Optional[Environment] = None):
        self.registry = registry
        self.jinja_env = jinja_env or registry.jinja_env

    async def _build_quota_section(
        self, scenes_data: Any, target_word_count: int, book_id: Optional[int] = None
    ) -> str:
        if isinstance(scenes_data, str):
            scenes_data = [{"action": scenes_data}]
        if not isinstance(scenes_data, list) or not scenes_data:
            return ""

        normalized_scenes = [s if isinstance(s, dict) else {"action": str(s)} for s in scenes_data]
        total_impact = sum(s.get("impact_score", 50) for s in normalized_scenes) or 1

        return await self.registry.render_async(
            "quota_section.j2",
            book_id=book_id,
            normalized_scenes=normalized_scenes,
            target_word_count=target_word_count,
            total_impact=total_impact,
        )

    async def _build_show_tell_section(
        self, scenes_data: Any, book_id: Optional[int] = None
    ) -> str:
        if isinstance(scenes_data, str):
            scenes_data = [{"action": scenes_data}]
        if not isinstance(scenes_data, list) or not scenes_data:
            return ""

        normalized_scenes = [s if isinstance(s, dict) else {"action": str(s)} for s in scenes_data]
        return await self.registry.render_async(
            "show_tell_section.j2", book_id=book_id, normalized_scenes=normalized_scenes
        )

    async def build_drafting_prompt(
        self,
        ep_num: int,
        plot_data: dict[str, Any],
        script_text: str,
        target_word_count: int,
        char_static_ctx: str,
        char_dynamic_ctx: str,
        prev_ctx: str,
        book_id: Optional[int] = None,
        **kwargs: Any,
    ) -> Tuple[str, str]:
        scenes_data = plot_data.get("scenes", [])
        quota_inst = await self._build_quota_section(
            scenes_data, target_word_count, book_id=book_id
        )
        show_tell_inst = await self._build_show_tell_section(scenes_data, book_id=book_id)

        settings_ctx = kwargs.get("settings_ctx", "{}")
        if isinstance(settings_ctx, str):
            try:
                settings_ctx = json.loads(settings_ctx)
            except json.JSONDecodeError:
                settings_ctx = {}
        if not isinstance(settings_ctx, dict):
            settings_ctx = {}

        assertion_inst = await self._build_assertion_section(
            settings_ctx.get("active_constraints", []), book_id=book_id
        )

        phase = plot_data.get("current_chain_phase", "Hate")
        tone_inst = await self.registry.render_async(
            "tone_instruction.j2", {"phase": phase}, book_id=book_id
        )

        style_key = kwargs.get("style_key", "style_web_standard")
        write_rule_type = kwargs.get("write_rule_type", "RULE_SET_A")
        style_inst = await self.build_style_instruction(style_key, book_id=book_id)

        from config.styles import get_rule_set

        rule_set_content = get_rule_set(write_rule_type)

        sys_inst = await self.registry.render_async(
            "drafting_system.j2",
            {
                "style_inst": style_inst,
                "rule_set_content": rule_set_content,
                "specialized_amp_inst": "",
            },
            book_id=book_id,
        )

        # ダイバージェンス指示のレンダリング（divergence_type_name が kwargs にある場合）
        divergence_type_name = kwargs.get("divergence_type_name", "safe")
        div_inst = await self.registry.render_async(
            "writing_divergence.j2", {"divergence_type_name": divergence_type_name}, book_id=book_id
        )

        user_prompt = await self.registry.render_async(
            "drafting_user.j2",
            {
                "quota_inst": quota_inst,
                "show_tell_inst": show_tell_inst,
                "assertion_inst": assertion_inst,
                "char_static_ctx": char_static_ctx,
                "char_dynamic_ctx": char_dynamic_ctx,
                "prev_ctx": prev_ctx,
                "script_text": script_text,
                "blueprint": plot_data.get("detailed_blueprint", ""),
                "target_word_count": target_word_count,
                "divergence_instruction": div_inst,
                "tone_inst": tone_inst,
                "director_notes": kwargs.get("director_notes"),
            },
            book_id=book_id,
        )
        return sys_inst, user_prompt

    async def build_final_writing_prompt(
        self,
        ep_num: int,
        plot_data: dict[str, Any],
        script_text: str,
        target_word_count: int,
        book_id: Optional[int] = None,
        **kwargs: Any,
    ) -> str:
        scenes_data = plot_data.get("scenes", [])
        quota_inst = await self._build_quota_section(
            scenes_data, target_word_count, book_id=book_id
        )
        show_tell_inst = await self._build_show_tell_section(scenes_data, book_id=book_id)
        forbidden_inst = await self._build_forbidden_section(book_id=book_id)
        hook_inst = await self._build_hook_strategy_section(book_id=book_id)

        settings_ctx = kwargs.get("settings_ctx", "{}")
        if isinstance(settings_ctx, str):
            try:
                settings_ctx = json.loads(settings_ctx)
            except Exception:
                settings_ctx = {}
        if not isinstance(settings_ctx, dict):
            settings_ctx = {}

        assertion_inst = await self._build_assertion_section(
            settings_ctx.get("active_constraints", []), book_id=book_id
        )

        phase = plot_data.get("current_chain_phase", "Hate")
        tone_inst = await self.registry.render_async(
            "tone_instruction.j2", {"phase": phase}, book_id=book_id
        )

        blueprint = plot_data.get("detailed_blueprint", "")
        if not blueprint and "blueprint" in kwargs:
            blueprint = kwargs.get("blueprint", "")

        context = WritingContext(
            ep_num=ep_num,
            target_word_count=target_word_count,
            char_static_ctx=kwargs.get("char_static_ctx", ""),
            char_dynamic_ctx=kwargs.get("char_dynamic_ctx", ""),
            prev_ctx=kwargs.get("prev_ctx", ""),
            pov_character_name=kwargs.get("pov_character_name", ""),
            density_level=kwargs.get("density_level", "Standard"),
            script_text=script_text,
            blueprint=blueprint,
            book_id=book_id,
        )
        context_dict = context.model_dump()
        context_dict.update(
            {
                "quota_inst": quota_inst,
                "show_tell_inst": show_tell_inst,
                "forbidden_inst": forbidden_inst,
                "hook_inst": hook_inst,
                "assertion_inst": assertion_inst,
                "tone_inst": tone_inst,
                "CONTENT_SEPARATOR": "---",
                "dialogue_profiles": kwargs.get("dialogue_profiles", {}),
            }
        )

        return await self.registry.render_async(
            "final_writing_prompt.j2", context_dict, book_id=book_id
        )

    async def build_polishing_prompt(
        self,
        draft_content: str,
        target_word_count: int,
        style_key: str,
        prose_sample: str,
        plot_data: Optional[dict[str, Any]] = None,
        use_beat_rules: bool = True,
        book_id: Optional[int] = None,
        **kwargs: Any,
    ) -> str:
        forbidden_inst = await self._build_forbidden_section(book_id=book_id)
        hook_inst = await self._build_hook_strategy_section(book_id=book_id)

        specialized_rules_data = []
        if use_beat_rules and plot_data:
            scenes = plot_data.get("scenes", [])
            for i, scene in enumerate(scenes):
                action = scene.get("action", "") if isinstance(scene, dict) else str(scene)
                specialized_rules_data.append({"scene_no": i + 1, "action": action})

        context = WritingContext(
            draft_content=draft_content,
            target_word_count=target_word_count,
            style_key=style_key,
            prose_sample=prose_sample,
            book_id=book_id,
        )
        context_dict = context.model_dump()
        context_dict.update(
            {
                "specialized_rules_data": specialized_rules_data,
                "forbidden_inst": forbidden_inst,
                "hook_inst": hook_inst,
                "style_sample": prose_sample,
                "draft_content": draft_content,
            }
        )
        context_dict.update(kwargs)

        return await self.registry.render_async(
            "polishing.j2", context_dict, book_id=book_id
        )

    async def build_critic_feedback_prompt(
        self, issue_list: Any, draft_content: str, blueprint: str, book_id: Optional[int] = None
    ) -> str:
        import json

        from src.models.audit import CriticFeedback

        issues_json = ""
        if hasattr(issue_list, "model_dump_json"):
            issues_json = issue_list.model_dump_json(indent=2)
        elif hasattr(issue_list, "dict"):
            issues_json = json.dumps(issue_list.dict(), ensure_ascii=False, indent=2)
        else:
            issues_json = str(issue_list)

        context = WritingContext(
            draft_content=draft_content,
            book_id=book_id,
        )
        context_dict = context.model_dump()
        context_dict.update(
            {
                "issues_json": issues_json,
                "blueprint": blueprint,
                "schema_json": json.dumps(
                    CriticFeedback.model_json_schema(), ensure_ascii=False, indent=2
                ),
            }
        )

        return await self.registry.render_async(
            "critic_feedback.j2", context_dict, book_id=book_id
        )

    async def build_fw_prompt(
        self,
        title: str,
        ep_num: int,
        static_ctx: str,
        dyn_ctx: str,
        prev_ctx: str,
        blueprint: str,
        book_id: Optional[int] = None,
        extra_instruction: str = "",
    ) -> str:
        context = WritingContext(
            title=title,
            ep_num=ep_num,
            static_ctx=static_ctx,
            dyn_ctx=dyn_ctx,
            prev_ctx=prev_ctx,
            blueprint=blueprint,
            extra_instruction=extra_instruction,
            book_id=book_id,
        )
        return await self.registry.render_async(
            "writing_context_prompt.j2", context.model_dump(), book_id=book_id
        )

    async def build_fw_prompt_from_structured_context(
        self,
        title: str,
        ep_num: int,
        context_data: Any,
        blueprint: str,
        book_id: Optional[int] = None,
        extra_instruction: str = "",
    ) -> str:
        static_ctx_lines = [
            f"■ {k}: {v}" for k, v in context_data.immutable.static_character_profiles.items()
        ]
        dyn_ctx_lines = [f"■ {k}: {v}" for k, v in context_data.dynamic.character_states.items()]

        static_ctx = "\n".join(static_ctx_lines)
        dyn_ctx = "\n".join(dyn_ctx_lines)
        prev_ctx = context_data.immutable.past_summary

        context = WritingContext(
            title=title,
            ep_num=ep_num,
            static_ctx=static_ctx,
            dyn_ctx=dyn_ctx,
            prev_ctx=prev_ctx,
            blueprint=blueprint,
            extra_instruction=extra_instruction,
            book_id=book_id,
        )
        return await self.registry.render_async(
            "writing_context_prompt.j2", context.model_dump(), book_id=book_id
        )

    async def build_dry_run_prompt(
        self,
        ep_num: int,
        improved_prompt: str,
        plot_detailed_blueprint: str,
        plot_script_content: str,
        book_id: Optional[int] = None,
    ) -> str:
        context = WritingContext(
            ep_num=ep_num,
            improved_prompt=improved_prompt,
            plot_detailed_blueprint=plot_detailed_blueprint,
            plot_script_content=plot_script_content,
            book_id=book_id,
        )
        return await self.registry.render_async(
            "dry_run_prompt.j2", context.model_dump(), book_id=book_id
        )

    async def build_rebuild_plot_outline_prompt(
        self,
        book_title: str,
        start_ep: int,
        new_total_eps: int,
        book_synopsis: str,
        keywords: str,
        trend_memo: str,
        pending_foreshadowing: list[str],
        book_id: Optional[int] = None,
        **kwargs: Any,
    ) -> str:
        context = WritingContext(
            book_title=book_title,
            start_ep=start_ep,
            new_total_eps=new_total_eps,
            book_synopsis=book_synopsis,
            keywords=keywords,
            trend_memo=trend_memo,
            book_id=book_id,
        )
        context_dict = context.model_dump()
        context_dict.update(
            {
                "pending_foreshadowing": pending_foreshadowing,
            }
        )
        context_dict.update(kwargs)

        return await self.registry.render_async(
            "rebuild_plot_outline_prompt.j2", context_dict, book_id=book_id
        )

    async def build_amplify_prompt(
        self,
        final_content: str,
        current_target_word_count: int,
        fix_inst: str = "",
        book_id: Optional[int] = None,
    ) -> str:
        context = WritingContext(
            final_content=final_content,
            current_target_word_count=current_target_word_count,
            fix_inst=fix_inst,
            book_id=book_id,
        )
        return await self.registry.render_async(
            "amplify_prompt.j2", context.model_dump(), book_id=book_id
        )

    async def build_analyze_import_chapter_prompt(
        self, cleaned_content: str, episode_draft_schema: Any, book_id: Optional[int] = None
    ) -> str:
        context = WritingContext(
            cleaned_content=cleaned_content[:5000],
            book_id=book_id,
        )
        context_dict = context.model_dump()
        if hasattr(episode_draft_schema, "model_json_schema"):
            context_dict["schema_json"] = episode_draft_schema.model_json_schema()
        else:
            context_dict["schema_json"] = episode_draft_schema
        return await self.registry.render_async(
            "analyze_import_chapter_prompt.j2", context_dict, book_id=book_id
        )

    async def build_critique_quality_prompt(
        self, book_title: str, summary_data_json: str, book_id: Optional[int] = None
    ) -> str:
        context = WritingContext(
            book_title=book_title,
            summary_data_json=summary_data_json,
            book_id=book_id,
        )
        return await self.registry.render_async(
            "critique_quality.j2", context.model_dump(), book_id=book_id
        )

    async def build_iterative_gap_analysis_prompt(
        self, book_genre: str, book_title: str, batch_data: str, book_id: Optional[int] = None
    ) -> str:
        context = WritingContext(
            book_genre=book_genre,
            book_title=book_title,
            batch_data=batch_data,
            book_id=book_id,
        )
        return await self.registry.render_async(
            "iterative_gap_analysis.j2", context.model_dump(), book_id=book_id
        )

    async def build_style_instruction(self, style_key: str, book_id: Optional[int] = None) -> str:
        from config.styles import STYLE_DEFINITIONS

        style_name = "標準文体"
        instruction = "標準的なWeb小説の文体を維持せよ。"
        dialogue_ratio = "50%"
        dna_data = None

        if style_key and style_key.startswith("custom_"):
            try:
                from src.backend.database import UnitOfWork
                from src.core.container import AppContainer

                c_id = int(style_key.replace("custom_", ""))
                async with UnitOfWork(AppContainer.db()) as uow:
                    custom_styles = await uow.misc.get_all_custom_styles()
                    for cs in custom_styles:
                        if (cs.id if hasattr(cs, "id") else cs.get("id")) == c_id:
                            style_name = cs.name if hasattr(cs, "name") else cs.get("name")
                            instruction = cs.instruction if hasattr(cs, "instruction") else cs.get("instruction")
                            break
            except Exception as e:
                logger.warning(f"Failed to fetch custom style {style_key}: {e}")
        elif style_key in STYLE_DEFINITIONS:
            style_def = STYLE_DEFINITIONS[style_key]
            style_name = style_def.get("name", style_key)
            instruction = style_def.get("instruction", "")
            dialogue_ratio = style_def.get("dialogue_ratio", "50%")
            dna_data = {
                "syntax_rhythm": style_def.get("syntax_rhythm", ""),
                "metaphor_dna": style_def.get("metaphor_dna", ""),
                "noise_dna": style_def.get("noise_dna", ""),
            }

        return await self.registry.render_async(
            "style_instruction.j2",
            book_id=book_id,
            style_key=style_key,
            style_name=style_name,
            instruction=instruction,
            dialogue_ratio=dialogue_ratio,
            dna_data=dna_data,
        )

    async def build_bible_extraction_prompt(self, content: str, book_id: Optional[int] = None) -> str:
        context = WritingContext(
            content=content,
            book_id=book_id,
        )
        return await self.registry.render_async(
            "bible_extraction.j2", context.model_dump(), book_id=book_id
        )

    async def get_villain_instruction(self, genre: str, book_id: Optional[int] = None) -> str:
        from src.core.plugin_loader import PluginLoader

        plugin = PluginLoader.get_instance().get_active_plugin()
        strategies = getattr(plugin, "villain_strategies", {})

        selected_strategy = strategies.get(
            "default", "敵対者は知略的であり、主人公を精神的に追い詰める戦略を採れ。"
        )
        for key, strategy in strategies.items():
            if key in genre:
                selected_strategy = strategy
                break

        context = WritingContext(
            genre=genre,
            book_id=book_id,
        )
        context_dict = context.model_dump()
        context_dict.update(
            {
                "strategy": selected_strategy,
                "genre": genre,
            }
        )
        return await self.registry.render_async(
            "villain_instruction.j2", context_dict, book_id=book_id
        )

    async def _build_forbidden_section(
        self, book_id: Optional[int] = None
    ) -> str:
        # Placeholder: no forbidden content
        return ""

    async def _build_hook_strategy_section(self, book_id: Optional[int] = None) -> str:
        return await self.registry.render_async("hook_strategy_section.j2", book_id=book_id)

    async def _build_assertion_section(
        self, constraints: List[Any], book_id: Optional[int] = None
    ) -> str:
        if not constraints:
            return ""
        return await self.registry.render_async(
            "assertion_section.j2", constraints=constraints, book_id=book_id
        )


    async def _build_refinement_prompt(
        self,
        content: str,
        style_key: str,
        is_light: bool,
        target_word_count: int,
        book_id: Optional[int] = None,
    ) -> str:
        context = WritingContext(
            content=content,
            style_key=style_key,
            is_light=is_light,
            target_word_count=target_word_count,
            book_id=book_id,
        )
        return await self.registry.render_async(
            "refinement_prompt.j2", context.model_dump(), book_id=book_id
        )
