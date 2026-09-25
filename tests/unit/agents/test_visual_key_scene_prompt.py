import jinja2
import os

def test_visual_key_scene_inclusion():
    env = jinja2.Environment(loader=jinja2.FileSystemLoader('prompts/templates/narrative'))
    template = env.get_template('final_writing_prompt.j2')
    # Render with minimal context
    rendered = template.render(
        quota_inst="",
        show_tell_inst="",
        forbidden_inst="",
        hook_inst="",
        assertion_inst="",
        char_static_ctx="",
        char_dynamic_ctx="",
        prev_ctx="",
        pov_character_name="",
        foreshadowing_context="",
        density_level="Standard",
        script_text="",
        blueprint="",
        target_word_count=0,
        tone_inst="",
        CONTENT_SEPARATOR="---",
        dialogue_profiles={}
    )
    assert "ビジュアルシーン（大ゴマ・見開き級）必須配置" in rendered