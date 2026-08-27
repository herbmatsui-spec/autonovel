from __future__ import annotations

import json
import logging
from typing import Any, Optional

from jinja2 import Environment

from prompts.plotting import EMOTIONAL_HOOK_TEMPLATE
from prompts.registry import PromptRegistry
from prompts.schemas import (
    AuditContext,
)

logger = logging.getLogger(__name__)


class NarrativePromptBuilder:
    """物語系プロンプト（世界創造、キャラ創造、プロット展開等）を構築するビルダー。"""

    def __init__(self, registry: PromptRegistry, jinja_env: Optional[Environment] = None):
        self.registry = registry
        self.jinja_env = jinja_env or registry.jinja_env

    async def build_world_creation_prompt(
        self,
        genre: str,
        keywords: str,
        response_schema: Any,
        book_id: Optional[int] = None,
        **kwargs: Any,
    ) -> str:
        context = AuditContext(
            genre=genre,
            keywords=keywords,
            book_id=book_id,
        )
        context_dict = context.model_dump()
        context_dict.update(kwargs)

        # Handle response_schema conversion
        if hasattr(response_schema, "model_json_schema"):
            context_dict["response_schema_json"] = response_schema.model_json_schema()
        else:
            context_dict["response_schema_json"] = response_schema

        return await self.registry.render_async(
            "world_creation_prompt.j2", context_dict, book_id=book_id
        )

    async def build_mc_creation_prompt(
        self,
        world_rules_json: str,
        genre: str,
        keywords: str,
        concept: str = "",
        book_id: Optional[int] = None,
        **kwargs: Any,
    ) -> str:
        context = AuditContext(
            world_rules_json=world_rules_json,
            genre=genre,
            keywords=keywords,
            concept=concept,
            book_id=book_id,
        )
        context_dict = context.model_dump()
        context_dict.update(kwargs)
        return await self.registry.render_async(
            "mc_creation_prompt.j2", context_dict, book_id=book_id
        )

    async def build_foreshadowing_extraction_prompt(
        self, plot_text: str, ep_num: int, book_id: Optional[int] = None
    ) -> str:
        context = AuditContext(
            plot_text=plot_text,
            ep_num=ep_num,
            book_id=book_id,
        )
        return await self.registry.render_async(
            "foreshadowing_extraction.j2", context.model_dump(), book_id=book_id
        )

    async def build_character_arc_extraction_prompt(
        self, plot_text: str, ep_num: int, book_id: Optional[int] = None
    ) -> str:
        context = AuditContext(
            plot_text=plot_text,
            ep_num=ep_num,
            book_id=book_id,
        )
        return await self.registry.render_async(
            "character_arc_extraction.j2", context.model_dump(), book_id=book_id
        )

    async def build_plot_expansion_prompt(
        self,
        book_title: str,
        ep_num: int,
        ep_info: Any,
        past_plots: list[Any],
        arcs: list[Any],
        book_genre: str,
        book_id: Optional[int] = None,
        emotional_hook: Any = None,
        **kwargs: Any,
    ) -> str:
        def safe_dict(obj: Any) -> dict[str, Any]:
            if isinstance(obj, dict):
                return obj
            if hasattr(obj, "model_dump") and callable(obj.model_dump):
                return obj.model_dump()
            if hasattr(obj, "dict") and callable(obj.dict):
                return obj.dict()
            return {
                k: getattr(obj, k)
                for k in [
                    "arc_num",
                    "title",
                    "start_ep",
                    "end_ep",
                    "one_line_summary",
                    "resolution_style",
                    "burned_cost_or_loot",
                    "thematic_milestone",
                    "antagonist_status",
                ]
                if hasattr(obj, k)
            }

        def fmt_arc(a):
            d = safe_dict(a)
            return f"- Arc {d.get('arc_num', '?')}: {d.get('title', '無題')} (Ep {d.get('start_ep', '?')}-{d.get('end_ep', '?')})"

        past_plots_str = (
            "\n".join(
                [
                    f"- 第{getattr(p, 'ep_num', '?')}話: {getattr(p, 'summary', '未定義')}"
                    for p in past_plots
                ]
            )
            if past_plots
            else "なし"
        )
        arcs_str = "\n".join([fmt_arc(a) for a in arcs]) if arcs else "なし"
        ep_info_dict = safe_dict(ep_info)

        from src.models.plot import PlotEpisode

        # ダイバージェンス指示のレンダリング
        divergence_inst = await self.registry.render_async(
            "divergence_instruction.j2", {}, book_id=book_id
        )

        context = AuditContext(
            book_title=book_title,
            ep_num=ep_num,
            book_genre=book_genre,
            book_id=book_id,
        )
        context_dict = context.model_dump()
        context_dict.update(
            {
                "one_line_summary": ep_info_dict.get("one_line_summary", "未定義"),
                "resolution_style": ep_info_dict.get("resolution_style", "Cheat"),
                "burned_cost_or_loot": ep_info_dict.get("burned_cost_or_loot", "なし"),
                "thematic_milestone": ep_info_dict.get("thematic_milestone", "なし"),
                "antagonist_status": ep_info_dict.get("antagonist_status", "現状維持"),
                "past_plots_str": past_plots_str,
                "arcs_str": arcs_str,
                "divergence_instruction": divergence_inst,
                "response_schema_json": PlotEpisode.model_json_schema(),
            }
        )
        context_dict.update(kwargs)

        prompt = await self.registry.render_async(
            "plot_expansion_prompt.j2", context_dict, book_id=book_id
        )

        if emotional_hook is not None:
            hook_text = EMOTIONAL_HOOK_TEMPLATE.format(
                one_line_intent=getattr(emotional_hook, "one_line_intent", str(emotional_hook)),
                target_tension_peak=getattr(emotional_hook, "target_tension_peak", 80),
            )
            prompt = f"{prompt}\n\n{hook_text}"

        return prompt

    async def build_ultra_fast_plot_batch_prompt(
        self,
        bible_json_str: str,
        ep_range: list[int],
        book_id: Optional[int] = None,
        enable_erotic: bool = False,
        erotic_intensity: int = 0,
        **kwargs: Any,
    ) -> str:
        bible_data = json.loads(bible_json_str) if bible_json_str else {}

        title = bible_data.get("title", "無題")
        genre = bible_data.get("genre", "ファンタジー")
        concept = bible_data.get("concept", "")
        style_key = bible_data.get("style_key", "style_web_standard")
        engine_key = bible_data.get("engine_key", "conflict")
        synopsis = bible_data.get("synopsis", "")

        mc_profile = bible_data.get("mc_profile", {})
        if hasattr(mc_profile, "model_dump"):
            mc_profile = mc_profile.model_dump()
        mc_name = mc_profile.get("name", "主人公") if isinstance(mc_profile, dict) else "主人公"
        mc_surface = mc_profile.get("surface_persona", "") if isinstance(mc_profile, dict) else ""
        mc_inner_conflict = (
            mc_profile.get("inner_conflict", "") if isinstance(mc_profile, dict) else ""
        )
        mc_iron_constraint = (
            mc_profile.get("iron_constraint", "") if isinstance(mc_profile, dict) else ""
        )

        sub_characters = bible_data.get("sub_characters", [])
        sub_char_summaries = []
        for sub in sub_characters:
            if hasattr(sub, "model_dump"):
                sub = sub.model_dump()
            if isinstance(sub, dict):
                name = sub.get("name", "")
                role = sub.get("role", "")
                profile = sub.get("profile", sub.get("personality", ""))
                sub_char_summaries.append(f"- {name} ({role}): {profile}")
        sub_characters_summary = "\n".join(sub_char_summaries) if sub_char_summaries else "なし"

        world_settings = bible_data.get("world_settings", {})
        if hasattr(world_settings, "model_dump"):
            world_settings = world_settings.model_dump()
        if isinstance(world_settings, dict):
            ws_parts = []
            for k, v in world_settings.items():
                if v and v != "なし" and v != 0 and v != []:
                    ws_parts.append(f"  - {k}: {v}")
            world_settings_summary = "\n".join(ws_parts) if ws_parts else "  (デフォルト)"
        else:
            world_settings_summary = "  (デフォルト)"

        roadmap_items = []
        full_roadmap = bible_data.get("full_story_roadmap", [])
        if not full_roadmap:
            full_roadmap = bible_data.get("roadmap", [])
        for item in full_roadmap:
            if hasattr(item, "model_dump"):
                item = item.model_dump()
            if isinstance(item, dict):
                ep_num = item.get("ep_num", item.get("episode_num", 0))
                if ep_num in ep_range:
                    roadmap_items.append(
                        {
                            "ep_num": ep_num,
                            "one_line_summary": item.get(
                                "one_line_summary", item.get("summary", "未定義")
                            ),
                            "resolution_style": item.get(
                                "resolution_style", item.get("style", "Cheat")
                            ),
                            "burned_cost_or_loot": item.get(
                                "burned_cost_or_loot", item.get("cost", "なし")
                            ),
                            "thematic_milestone": item.get("thematic_milestone", "なし"),
                            "antagonist_status": item.get(
                                "antagonist_status", item.get("enemy_status", "現状維持")
                            ),
                        }
                    )

        if len(ep_range) == 1:
            ep_range_str = f"第{ep_range[0]}話"
        else:
            ep_range_str = f"第{ep_range[0]}話〜第{ep_range[-1]}話"

        from src.models.plot import UltraFastPlotBatch

        schema_json = json.dumps(
            UltraFastPlotBatch.model_json_schema(), ensure_ascii=False, indent=2
        )

        context = AuditContext(
            book_title=title,
            book_genre=genre,
            concept=concept,
            style_key=style_key,
            engine_key=engine_key,
            synopsis=synopsis,
            mc_name=mc_name,
            mc_surface=mc_surface,
            mc_inner_conflict=mc_inner_conflict,
            mc_iron_constraint=mc_iron_constraint,
            world_settings_summary=world_settings_summary,
            sub_characters_summary=sub_characters_summary,
            ep_range_str=ep_range_str,
            book_id=book_id,
        )
        context_dict = context.model_dump()
        context_dict.update(
            {
                "roadmap_items": roadmap_items,
                "response_schema_json": schema_json,
            }
        )

        prompt = await self.registry.render_async(
            "ultra_fast_plot_batch_prompt.j2", context_dict, book_id=book_id
        )

        is_erotic = enable_erotic or kwargs.get("enable_erotic", False)
        intensity = erotic_intensity or kwargs.get("erotic_intensity", 2)
        if is_erotic and intensity > 0:
            prompt += (
                f"\n\n【官能・情愛プロット配置指針（強度: {intensity}）】\n"
                f"各話のプロット構築において、キャラクター間の距離感の変化、心理的葛藤、"
                f"官能的緊張（Build）や親密な触れ合い・感情のピーク（Peak）、およびその後の余韻（Afterglow）の配置を意識してストーリーラインを構成してください。"
            )

        return prompt

    async def build_bible_creation_prompt(
        self,
        bible_core_schema: Any = None,
        world_rules_json: str = "{}",
        genre: str = "ファンタジー",
        keywords: str = "",
        concept: str = "",
        target_eps: int = 10,
        book_id: Optional[int] = None,
        title: str = "",
        style_key: str = "style_web_standard",
        engine_key: str = "conflict",
        enable_erotic: bool = False,
        erotic_intensity: int = 0,
        **kwargs: Any,
    ) -> str:
        """覇権企画書（WorldBible）作成用プロンプトを構築する。"""
        schema_json = ""
        if bible_core_schema is not None:
            if hasattr(bible_core_schema, "model_json_schema"):
                schema_json = json.dumps(
                    bible_core_schema.model_json_schema(), ensure_ascii=False, indent=2
                )
            elif isinstance(bible_core_schema, dict):
                schema_json = json.dumps(bible_core_schema, ensure_ascii=False, indent=2)
            else:
                schema_json = str(bible_core_schema)

        context_dict = {
            "target_eps": target_eps,
            "world_rules_json": world_rules_json,
            "concept": concept or keywords or genre,
            "genre": genre,
            "keywords": keywords,
            "title": title,
            "style_key": style_key,
            "engine_key": engine_key,
            "schema_json": schema_json,
            "book_id": book_id,
        }
        context_dict.update(kwargs)

        template_name = "bible_zamaa_template.j2" if engine_key == "zamaa" else "bible_creation_prompt.j2"
        prompt = await self.registry.render_async(template_name, context_dict, book_id=book_id)

        if enable_erotic or kwargs.get("enable_erotic", False):
            intensity = erotic_intensity or kwargs.get("erotic_intensity", 2)
            prompt += (
                f"\n\n【官能・成人向け企画指針（過激度: {intensity}）】\n"
                f"本作は大人向けの情愛・官能要素（NSFW）を含む作品です。"
                f"企画書および登場人物設定・ロードマップにおいて、キャラクター間の感情の機微、"
                f"身体的・精神的な惹かれ合い、関係性の深まりと葛藤を核となるテーマの一つとして組み込んでください。"
            )

        return prompt

    async def build_sharp_edge_proposal_prompt(
        self, plot_summary: str, book_id: Optional[int] = None
    ) -> str:
        from prompts.plotting import SHARP_EDGE_PROPOSAL_TEMPLATE

        prompt = SHARP_EDGE_PROPOSAL_TEMPLATE.format(plot_summary=plot_summary)
        return prompt

    async def build_early_entertainment_check_prompt(
        self, rough_plot: str, opening_500_chars: str, book_id: Optional[int] = None
    ) -> str:
        from prompts.plotting import EARLY_ENTERTAINMENT_CHECK_TEMPLATE

        prompt = EARLY_ENTERTAINMENT_CHECK_TEMPLATE.format(
            rough_plot=rough_plot,
            opening_500_chars=opening_500_chars[:500],
        )
        return prompt
