import json
import unittest

from jinja2 import Environment

from src.backend.engine_prompts import PromptManager


class TestAPCandDeltaPolish(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.jinja_env = Environment()
        # Mock style_instruction template for PromptManager
        self.jinja_env.globals.update({"CONTENT_SEPARATOR": "===SEPARATOR==="})
        # Add basic dummy template
        self.jinja_env.loader = None
        self.pm = PromptManager(self.jinja_env)

        # Patch get_style_instruction to avoid needing actual jinja environment files if not present
        async def mock_get_style(style_key, book_id=None, **kwargs):
            return f"Style: {style_key}"
        self.pm.get_style_instruction = mock_get_style

    async def test_apc_system_prompt_determinism(self):
        style_key = "style_web_standard"
        write_rule_type = "RULE_SET_A"
        settings_ctx_json = json.dumps({"theme": "Dark Fantasy", "rules": [1, 2, 3]}, sort_keys=True)
        hooks_inst = "■ Hero: Use sword\n■ Villain: Laugh evilly"
        char_static_ctx = "■ Hero (Protagonist)\n■ Villain (Antagonist)"

        # Generate prompt twice with the same inputs to check absolute identical value
        prompt1 = await self.pm.build_apc_system_prompt(style_key, write_rule_type, settings_ctx_json, hooks_inst, char_static_ctx)
        prompt2 = await self.pm.build_apc_system_prompt(style_key, write_rule_type, settings_ctx_json, hooks_inst, char_static_ctx)

        self.assertEqual(prompt1, prompt2)
        self.assertIn("【キャラクター不変属性】", prompt1)
        self.assertIn("【作品設定・描写フック】", prompt1)

    async def test_beat_mapping_prompt(self):
        final_content = "This is the first paragraph. This is the second paragraph."
        beats = ["Scene 1 - Beat 1: Intro", "Scene 1 - Beat 2: Climax"]

        prompt = await self.pm.build_beat_mapping_prompt(final_content, beats)
        self.assertIn("【ビートリスト】", prompt)
        self.assertIn("【小説本文】", prompt)
        self.assertIn("Scene 1 - Beat 1: Intro", prompt)

    async def test_delta_polish_prompt(self):
        target_beat = "He walked to the gate."
        target_word_count = 300
        prefix_text = "The sun was rising."
        suffix_text = "He opened it."
        instructions = "Add sensory descriptions of the gate."

        prompt = await self.pm.build_delta_polish_prompt(target_beat, target_word_count, prefix_text, suffix_text, instructions)
        self.assertIn("【対象ビートの草稿】", prompt)
        self.assertIn("【指示・条件】", prompt)
        self.assertIn("Add sensory descriptions of the gate.", prompt)
        self.assertIn("He walked to the gate.", prompt)

if __name__ == "__main__":
    unittest.main()
