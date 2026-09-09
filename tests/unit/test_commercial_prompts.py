"""
Unit tests for prompts/commercial_prompts.py

Verifies that commercial prompts:
1. Contain no Korean (Hangul) characters.
2. Contain no Russian (Cyrillic) characters.
3. Contain no Simplified Chinese or non-Japanese standard characters (all valid in standard Japanese CP932).
4. All registry and generation functions execute successfully and produce well-formed prompt strings.
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

# Ensure project root is in sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from prompts.commercial_prompts import (
    AB_TEST_PROMPTS,
    COMMERCIAL_ROLE_PROMPT_TEMPLATES,
    MARKETING_PROMPT_TEMPLATES,
    PLEASURE_GRAPH_PROMPT_TEMPLATES,
    SERIES_EXPENSION_PROMPTS,
    STYLE_DNA_PROMPT_TEMPLATES,
    ab_test_prompt_registry,
    commercial_role_prompt_registry,
    generate_commercial_role_summary,
    generate_full_commercial_prompt_pack,
    generate_pleasure_graph_prompt,
    marketing_prompt_registry,
    pleasure_prompt_registry,
    series_prompt_registry,
    style_prompt_registry,
)


class TestCommercialPrompts(unittest.TestCase):
    def setUp(self):
        self.file_path = Path(__file__).resolve().parent.parent.parent / "prompts" / "commercial_prompts.py"

    def test_no_hangul_in_commercial_prompts(self):
        """Verify that no Korean (Hangul) characters are present in commercial_prompts.py."""
        content = self.file_path.read_text(encoding="utf-8")
        hangul_matches = re.findall(r"[\uac00-\ud7af\u1100-\u11ff]", content)
        self.assertFalse(hangul_matches, f"Found Hangul characters: {hangul_matches}")

    def test_no_cyrillic_in_commercial_prompts(self):
        """Verify that no Russian (Cyrillic) characters are present in commercial_prompts.py."""
        content = self.file_path.read_text(encoding="utf-8")
        cyrillic_matches = re.findall(r"[\u0400-\u04ff]", content)
        self.assertFalse(cyrillic_matches, f"Found Cyrillic characters: {cyrillic_matches}")

    def test_all_characters_valid_in_standard_japanese_encoding(self):
        """
        Verify that all characters in commercial_prompts.py are valid in standard Japanese CP932 encoding.
        This guarantees that Simplified Chinese, Latin middle dots (·), and other foreign Unicode noise are purged.
        """
        lines = self.file_path.read_text(encoding="utf-8").splitlines()
        non_cp932 = []
        for line_no, line in enumerate(lines, 1):
            for ch in line:
                try:
                    ch.encode("cp932")
                except UnicodeEncodeError:
                    non_cp932.append((line_no, ch, line.strip()))

        self.assertFalse(non_cp932, f"Found non-CP932 characters: {non_cp932}")

    def test_commercial_role_prompt_registry(self):
        """Verify commercial_role_prompt_registry returns valid Japanese prompt strings for all roles."""
        roles = [
            "avatar_of_desire",
            "hate_magnet",
            "unconditional_supporter",
            "contrast_engine",
            "unique_value",
            "growth_investment",
            "destined_resonance",
            "information_hegemony",
            "status_flip_trigger",
        ]
        for role in roles:
            prompt_scene = commercial_role_prompt_registry(role, character_name="アレン", prompt_type="scene_generation")
            self.assertIn("アレン", prompt_scene)
            self.assertGreater(len(prompt_scene), 50)

            prompt_build = commercial_role_prompt_registry(role, character_name="アレン", prompt_type="character_building")
            self.assertIn("アレン", prompt_build)
            self.assertGreater(len(prompt_build), 30)

    def test_generate_commercial_role_summary(self):
        """Verify generate_commercial_role_summary produces formatted summary."""
        roles = ["avatar_of_desire", "growth_investment"]
        summary = generate_commercial_role_summary("アレン", roles)
        self.assertIn("【アレンの商業的役割サマリー】", summary)
        self.assertIn("自己投影・願望充足役", summary)
        self.assertIn("成長可視化・投資心理喚起", summary)

    def test_pleasure_prompt_registry(self):
        """Verify pleasure_prompt_registry returns valid strings for all pleasure types."""
        types = [
            "catharsis_building",
            "schadenfreude_building",
            "tension_release_building",
            "superiority_building",
            "intimacy_building",
        ]
        for ptype in types:
            prompt = pleasure_prompt_registry(ptype)
            self.assertGreater(len(prompt), 40)
            self.assertIn("【", prompt)

    def test_generate_pleasure_graph_prompt(self):
        """Verify generate_pleasure_graph_prompt adapts across different story progress phases."""
        intro = generate_pleasure_graph_prompt(0.1)
        self.assertIn("導入期", intro)

        mid = generate_pleasure_graph_prompt(0.5)
        self.assertIn("展開期", mid)

        pre_climax = generate_pleasure_graph_prompt(0.75)
        self.assertIn("クライマックス直前期", pre_climax)

        climax = generate_pleasure_graph_prompt(0.9)
        self.assertIn("決戦期", climax)

    def test_marketing_prompt_registry(self):
        """Verify marketing_prompt_registry returns valid marketing prompt templates."""
        types = ["hook_generation", "tagline_generation", "synopsis_generation"]
        for mtype in types:
            prompt = marketing_prompt_registry(mtype)
            self.assertGreater(len(prompt), 30)

    def test_style_prompt_registry(self):
        """Verify style_prompt_registry returns valid style DNA prompt templates."""
        types = ["voice_extraction", "character_voice_extraction", "rhythm_pattern_extraction"]
        for stype in types:
            prompt = style_prompt_registry(stype)
            self.assertGreater(len(prompt), 30)

    def test_series_prompt_registry(self):
        """Verify series_prompt_registry returns valid series expansion prompts."""
        types = ["arc_planning", "sequel_hooks", "filler_strategy"]
        for stype in types:
            prompt = series_prompt_registry(stype)
            self.assertGreater(len(prompt), 30)

    def test_ab_test_prompt_registry(self):
        """Verify ab_test_prompt_registry returns valid A/B test prompts."""
        types = ["opening_variation", "conflictr_resolution_variation", "romance_development_variation"]
        for atype in types:
            prompt = ab_test_prompt_registry(atype)
            self.assertGreater(len(prompt), 30)
            self.assertIn("バリエーション", prompt)

    def test_generate_full_commercial_prompt_pack(self):
        """Verify generate_full_commercial_prompt_pack generates complete dictionary of prompt packs."""
        roles = ["avatar_of_desire", "contrast_engine"]
        pack_web = generate_full_commercial_prompt_pack("エリス", roles, target_market="web novel")

        self.assertIn("commercial_role_avatar_of_desire", pack_web)
        self.assertIn("commercial_role_contrast_engine", pack_web)
        self.assertIn("pleasure_catharsis", pack_web)
        self.assertIn("marketing_hook", pack_web)
        self.assertIn("style_voice", pack_web)
        self.assertIn("series_arc", pack_web)
        self.assertIn("ab_opening", pack_web)
        self.assertIn("platform_optimization", pack_web)
        self.assertIn("ウェブ小説", pack_web["platform_optimization"])

        pack_kindle = generate_full_commercial_prompt_pack("エリス", roles, target_market="kindle")
        self.assertIn("Kindle", pack_kindle["platform_optimization"])


if __name__ == "__main__":
    unittest.main()
