# -*- coding: utf-8 -*-
import os
import sys

sys.path.append(os.getcwd())

import unittest

from jinja2 import DictLoader, Environment

from config import PROMPT_TEMPLATES
from prompts.context import (
    BibleCreationContext,
    CharacterConceptContext,
    FinalWritingContext,
    HegemonyDogfeedingContext,
    McCreationContext,
    PlotExpansionContext,
    RebuildPlotOutlineContext,
    RoadmapPromptContext,
    RoadmapRebuildContext,
    SubCharCreationContext,
    TitleGenerationContext,
)
from prompts.manager import PromptManager


class TestPromptContext(unittest.TestCase):
    def setUp(self):
        # Mocking Jinja environment
        self.jinja_env = Environment(loader=DictLoader(PROMPT_TEMPLATES))
        self.pm = PromptManager(self.jinja_env)

    def test_build_character_concept_prompt(self):
        # 1. Individual args
        res_indiv = self.pm.build_character_concept_prompt(
            None, "fantasy", "magic, sword", "hero", "my hook", "comfort"
        )
        # 2. Context
        ctx = CharacterConceptContext(
            genre="fantasy",
            keywords="magic, sword",
            archetype="hero",
            custom_hook="my hook",
            engine_key="comfort"
        )
        res_ctx = self.pm.build_character_concept_prompt(context=ctx)
        self.assertEqual(res_indiv, res_ctx)

    def test_build_title_generation_prompt(self):
        res_indiv = self.pm.build_title_generation_prompt(
            None, "fantasy", "magic, sword", "trend info", "my hook", "enigma"
        )
        ctx = TitleGenerationContext(
            genre="fantasy",
            keywords="magic, sword",
            trend_instruction="trend info",
            custom_hook="my hook",
            engine_key="enigma"
        )
        res_ctx = self.pm.build_title_generation_prompt(context=ctx)
        self.assertEqual(res_indiv, res_ctx)

    def test_build_mc_creation_prompt(self):
        res_indiv = self.pm.build_mc_creation_prompt(
            None, "{}", "fantasy", "magic, sword", "hero concept", "style_web_standard", "conflict"
        )
        ctx = McCreationContext(
            world_rules_json="{}",
            genre="fantasy",
            keywords="magic, sword",
            concept="hero concept",
            style_key="style_web_standard",
            engine_key="conflict"
        )
        res_ctx = self.pm.build_mc_creation_prompt(context=ctx)
        self.assertEqual(res_indiv, res_ctx)

    def test_build_sub_char_creation_prompt(self):
        res_indiv = self.pm.build_sub_char_creation_prompt(
            None, "{}", "{}", [], "MC_Name", "fantasy", "magic"
        )
        ctx = SubCharCreationContext(
            world_rules_json="{}",
            mc_data_json="{}",
            causality_map=[],
            mc_name="MC_Name",
            genre="fantasy",
            keywords="magic"
        )
        res_ctx = self.pm.build_sub_char_creation_prompt(context=ctx)
        self.assertEqual(res_indiv, res_ctx)

    def test_build_bible_creation_prompt(self):
        # We need a dummy BaseModel
        from pydantic import BaseModel
        class DummyBibleSchema(BaseModel):
            pass
        res_indiv = self.pm.build_bible_creation_prompt(
            None, DummyBibleSchema, "{}", "concept desc", 10, "fantasy", "style_web_standard", "conflict"
        )
        ctx = BibleCreationContext(
            bible_core_schema=DummyBibleSchema,
            world_rules_json="{}",
            concept="concept desc",
            target_eps=10,
            genre="fantasy",
            style_key="style_web_standard",
            engine_key="conflict"
        )
        res_ctx = self.pm.build_bible_creation_prompt(context=ctx)
        self.assertEqual(res_indiv, res_ctx)

    def test_build_roadmap_prompt(self):
        from pydantic import BaseModel
        class DummyRoadmapSchema(BaseModel):
            pass
        res_indiv = self.pm.build_roadmap_prompt(
            None, "Title", "Synopsis", 10, DummyRoadmapSchema, "fantasy", "enigma"
        )
        ctx = RoadmapPromptContext(
            bible_core_title="Title",
            bible_core_synopsis="Synopsis",
            target_eps=10,
            roadmap_list_schema=DummyRoadmapSchema,
            genre="fantasy",
            engine_key="enigma"
        )
        res_ctx = self.pm.build_roadmap_prompt(context=ctx)
        self.assertEqual(res_indiv, res_ctx)

    def test_build_plot_expansion_prompt(self):
        ep_info = {"one_line_summary": "summary", "resolution_style": "Cheat"}
        res_indiv = self.pm.build_plot_expansion_prompt(
            None, "Title", 1, ep_info, [], [], "fantasy", 10, "inst", "enigma", {}, [], {}
        )
        ctx = PlotExpansionContext(
            book_title="Title",
            ep_num=1,
            ep_info=ep_info,
            past_plots=[],
            arcs=[],
            book_genre="fantasy",
            current_stress=10,
            narrative_instruction="inst",
            engine_key="enigma",
            truth_ledger={},
            foreshadowing_map=[],
            world_rules={}
        )
        res_ctx = self.pm.build_plot_expansion_prompt(context=ctx)
        self.assertEqual(res_indiv, res_ctx)

    def test_build_rebuild_plot_outline_prompt(self):
        res_indiv = self.pm.build_rebuild_plot_outline_prompt(
            None, "Title", 1, 10, "synopsis", "keywords", "trend", ["fs1", "fs2"], "fantasy", "conflict"
        )
        ctx = RebuildPlotOutlineContext(
            book_title="Title",
            start_ep=1,
            new_total_eps=10,
            book_synopsis="synopsis",
            keywords="keywords",
            trend_memo="trend",
            pending_foreshadowing=["fs1", "fs2"],
            genre="fantasy",
            engine_key="conflict"
        )
        res_ctx = self.pm.build_rebuild_plot_outline_prompt(context=ctx)
        self.assertEqual(res_indiv, res_ctx)

    def test_build_roadmap_rebuild_prompt(self):
        res_indiv = self.pm.build_roadmap_rebuild_prompt(
            None, "Title", "synopsis", 1, 10, "keywords", "trend", "pattern", "fantasy", "conflict"
        )
        ctx = RoadmapRebuildContext(
            title="Title",
            synopsis="synopsis",
            start_ep=1,
            new_total_eps=10,
            keywords="keywords",
            trend_memo="trend",
            plot_pattern_key="pattern",
            genre="fantasy",
            engine_key="conflict"
        )
        res_ctx = self.pm.build_roadmap_rebuild_prompt(context=ctx)
        self.assertEqual(res_indiv, res_ctx)

    def test_build_final_writing_prompt(self):
        import random
        plot_data = {"scenes": []}

        random.seed(42)
        res_indiv = self.pm.build_final_writing_prompt(
            None, 1, plot_data, "script text", 1000, "thought", {}, [], genre_str="fantasy", engine_key="enigma"
        )

        random.seed(42)
        ctx = FinalWritingContext(
            ep_num=1,
            plot_data=plot_data,
            script_text="script text",
            target_word_count=1000,
            plot_thought_process="thought",
            truth_ledger={},
            foreshadowing_map=[],
            kwargs={"genre_str": "fantasy", "engine_key": "enigma"}
        )
        res_ctx = self.pm.build_final_writing_prompt(context=ctx)

        if res_indiv != res_ctx:
            print("--- res_indiv[0] ---")
            print(res_indiv[0][:1000])
            print("--- res_ctx[0] ---")
            print(res_ctx[0][:1000])

            import difflib
            diff = list(difflib.unified_diff(
                res_indiv[0].splitlines(),
                res_ctx[0].splitlines(),
                fromfile='res_indiv',
                tofile='res_ctx'
            ))
            print("\n".join(diff[:50]))

        self.assertEqual(res_indiv, res_ctx)

    def test_build_hegemony_dogfeeding_prompt(self):
        res_indiv = self.pm.build_hegemony_dogfeeding_prompt(
            None, "fantasy", "Title", "samples", "source", "bible_summary", 0, {}, [], "conflict"
        )
        ctx = HegemonyDogfeedingContext(
            genre="fantasy",
            title="Title",
            samples="samples",
            source_code="source",
            bible_summary="bible_summary",
            contamination_score=0,
            contamination_map={},
            axes=[],
            engine_key="conflict"
        )
        res_ctx = self.pm.build_hegemony_dogfeeding_prompt(context=ctx)
        self.assertEqual(res_indiv, res_ctx)

if __name__ == "__main__":
    unittest.main()

