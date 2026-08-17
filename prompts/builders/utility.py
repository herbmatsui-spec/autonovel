from __future__ import annotations

import logging
from typing import Any, Optional

from jinja2 import Environment

from prompts.registry import PromptRegistry
from prompts.schemas import UtilityContext

logger = logging.getLogger(__name__)


class UtilityPromptBuilder:
    """ユーティリティ系プロンプト（マーケティング、タイトル等）を構築するビルダー。"""

    def __init__(self, registry: PromptRegistry, jinja_env: Optional[Environment] = None):
        self.registry = registry
        self.jinja_env = jinja_env or registry.jinja_env

    async def build_marketing_pack_prompt(
        self, book_title: str, synopsis: str, latest_ep: int, book_id: Optional[int] = None
    ) -> str:
        context = UtilityContext(
            book_title=book_title,
            synopsis=synopsis,
            latest_ep=latest_ep,
            book_id=book_id,
        )
        return await self.registry.render_async(
            "marketing_pack_prompt.j2", context.model_dump(), book_id=book_id
        )

    async def build_title_generation_prompt(
        self, genre: str, keywords: str, book_id: Optional[int] = None
    ) -> str:
        context = UtilityContext(
            genre=genre,
            keywords=keywords,
            book_id=book_id,
        )
        return await self.registry.render_async(
            "title_generation_prompt.j2", context.model_dump(), book_id=book_id
        )

    async def build_style_dna_analysis_prompt(
        self, sample_text: str, book_id: Optional[int] = None
    ) -> str:
        context = UtilityContext(
            sample_text=sample_text[:3000],  # Truncate to 3000 chars like in original
            book_id=book_id,
        )
        return await self.registry.render_async(
            "style_dna_analysis_prompt.j2", context.model_dump(), book_id=book_id
        )

    async def build_global_repair_prompt(
        self,
        conflict_report: str,
        synopsis: str,
        world_rules: str,
        mc_profile: str,
        book_id: Optional[int] = None,
        **kwargs: Any,
    ) -> str:
        # Note: This is actually in AuditPromptBuilder, but keeping here for completeness
        # In the actual implementation, this should be moved to AuditPromptBuilder
        context = UtilityContext(
            conflict_report=conflict_report,
            synopsis=synopsis,
            world_rules=world_rules,
            mc_profile=mc_profile,
            book_id=book_id,
        )
        context_dict = context.model_dump()
        context_dict.update(kwargs)
        return await self.registry.render_async(
            "global_repair_prompt.j2", context_dict, book_id=book_id
        )

    async def build_fast_plot_screen_prompt(
        self, blueprint: str, book_id: Optional[int] = None
    ) -> str:
        context = UtilityContext(
            blueprint=blueprint,
            book_id=book_id,
        )
        return await self.registry.render_async(
            "fast_plot_screen_prompt.j2", context.model_dump(), book_id=book_id
        )

    async def build_ability_audit_prompt(
        self,
        blueprint: str,
        settings_json: str,
        characters_json: str,
        book_id: Optional[int] = None,
    ) -> str:
        # Note: This is actually in AuditPromptBuilder
        context = UtilityContext(
            blueprint=blueprint,
            settings_json=settings_json,
            characters_json=characters_json,
            book_id=book_id,
        )
        return await self.registry.render_async(
            "ability_audit_prompt.j2", context.model_dump(), book_id=book_id
        )

    async def build_deai_audit_prompt(self, content: str, book_id: Optional[int] = None) -> str:
        # Note: This is actually in AuditPromptBuilder
        context = UtilityContext(
            content=content[:4000],
            book_id=book_id,
        )
        return await self.registry.render_async(
            "deai_audit_prompt.j2", context.model_dump(), book_id=book_id
        )

    async def build_deai_propose_rules_prompt(
        self, content: str, domain: str, book_id: Optional[int] = None
    ) -> str:
        # Note: This is actually in AuditPromptBuilder
        context = UtilityContext(
            content=content[:4000],
            book_id=book_id,
        )
        context_dict = context.model_dump()
        context_dict["domain"] = domain
        return await self.registry.render_async(
            "deai_propose_rules_prompt.j2", context_dict, book_id=book_id
        )

    async def build_apc_system_prompt(
        self,
        style_key: str,
        write_rule_type: str,
        settings_ctx_json: str,
        hooks_inst: str,
        char_static_ctx: str,
        book_id: Optional[int] = None,
    ) -> str:
        style_inst = await self.build_style_instruction(style_key, book_id=book_id)
        from config.styles import get_rule_set

        rule_set_content = get_rule_set(write_rule_type)

        # logic for direction
        # simplified direction logic or delegate to a template
        direction = "heavy"  # Default or calculate based on style_key
        if "light" in style_key or "short" in style_key:
            direction = "light"

        commercial_inst = await self.registry.render_async(
            "commercial_protocol.j2", direction=direction, book_id=book_id
        )
        hook_inst = await self._build_hook_strategy_section(book_id=book_id)

        context = UtilityContext(
            style_key=style_key,
            write_rule_type=write_rule_type,
            settings_ctx_json=settings_ctx_json,
            hooks_inst=hook_inst,
            char_static_ctx=char_static_ctx,
            book_id=book_id,
        )
        context_dict = context.model_dump()
        context_dict.update(
            {
                "style_inst": style_inst,
                "rule_set_content": rule_set_content,
                "commercial_inst": commercial_inst,
                "hooks_inst": hook_inst,
            }
        )

        return await self.registry.render_async(
            "apc_system.j2", context_dict, book_id=book_id
        )

    async def build_beat_mapping_prompt(
        self, final_content: str, beats: list[str], book_id: Optional[int] = None
    ) -> str:
        import json

        context = UtilityContext(
            final_content=final_content,
            book_id=book_id,
        )
        context_dict = context.model_dump()
        context_dict.update(
            {
                "beats_json": json.dumps(beats, ensure_ascii=False, indent=2),
            }
        )

        return await self.registry.render_async(
            "beat_mapping_prompt.j2", context_dict, book_id=book_id
        )

    async def build_delta_polish_prompt(
        self,
        target_beat: str,
        target_word_count: int,
        prefix_text: str,
        suffix_text: str,
        instructions: str,
        book_id: Optional[int] = None,
    ) -> str:
        context = UtilityContext(
            target_beat=target_beat,
            target_word_count=target_word_count,
            prefix_text=prefix_text,
            suffix_text=suffix_text,
            instructions=instructions,
            book_id=book_id,
        )
        return await self.registry.render_async(
            "delta_polish_prompt.j2", context.model_dump(), book_id=book_id
        )

    async def build_marketing_ab_test_prompt(
        self, bible_core_concept: str, book_id: Optional[int] = None, **kwargs: Any
    ) -> str:
        context = UtilityContext(
            bible_core_concept=bible_core_concept,
            book_id=book_id,
        )
        context_dict = context.model_dump()
        context_dict.update(kwargs)
        return await self.registry.render_async(
            "marketing_ab_test_prompt.j2", context_dict, book_id=book_id
        )

    async def build_roadmap_prompt(
        self,
        bible_core_title: str,
        bible_core_synopsis: str,
        target_eps: int,
        roadmap_list_schema: Any,
        book_id: Optional[int] = None,
        **kwargs: Any,
    ) -> str:
        context = UtilityContext(
            bible_core_title=bible_core_title,
            bible_core_synopsis=bible_core_synopsis,
            target_eps=target_eps,
            book_id=book_id,
        )
        context_dict = context.model_dump()
        if hasattr(roadmap_list_schema, "model_json_schema"):
            context_dict["schema_json"] = roadmap_list_schema.model_json_schema()
        else:
            context_dict["schema_json"] = roadmap_list_schema
        context_dict.update(kwargs)
        return await self.registry.render_async(
            "roadmap_prompt.j2", context_dict, book_id=book_id
        )

    async def build_analyze_import_chapter_prompt(
        self, cleaned_content: str, episode_draft_schema: Any, book_id: Optional[int] = None
    ) -> str:
        # Note: This is actually in WritingPromptBuilder
        context = UtilityContext(
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
        # Note: This is actually in WritingPromptBuilder
        context = UtilityContext(
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
        # Note: This is actually in WritingPromptBuilder
        context = UtilityContext(
            book_genre=book_genre,
            book_title=book_title,
            batch_data=batch_data,
            book_id=book_id,
        )
        return await self.registry.render_async(
            "iterative_gap_analysis.j2", context.model_dump(), book_id=book_id
        )

    async def _build_hook_strategy_section(self, book_id: Optional[int] = None) -> str:
        return await self.registry.render_async("hook_strategy_section.j2", book_id=book_id)

    async def build_style_instruction(self, style_key: str, book_id: Optional[int] = None) -> str:
        return await self.registry.render_async(
            "style_instruction.j2", book_id=book_id, style_key=style_key
        )
