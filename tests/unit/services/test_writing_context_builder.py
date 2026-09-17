from src.services.writing_services import WritingGenerationContext

def test_writing_generation_context_build_sys_inst():
    ctx = WritingGenerationContext(
        sys_inst="基本指示",
        pov_instruction="一人称視点（私）で記述せよ",
        style_key="web_novel_fast",
        target_word_count=3000
    )
    sys_inst = ctx.build_sys_inst()
    assert "基本指示" in sys_inst
    assert "一人称視点" in sys_inst
