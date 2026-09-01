from src.services.writing_services import WritingGenerationContext


def test_writing_generation_context_defaults():
    """WritingGenerationContext のデフォルト値と設定検証。"""
    ctx = WritingGenerationContext(
        sys_inst="あなたはプロの小説家です。",
        pov_instruction="三人称視点",
        feedback_patch="テンポを速めること",
        style_key="style_web_standard",
        target_word_count=2500,
    )

    assert ctx.style_key == "style_web_standard"
    assert ctx.target_word_count == 2500
    assert ctx.enable_polishing is True

    sys_inst = ctx.build_sys_inst()
    assert "あなたはプロの小説家です。" in sys_inst
    assert "三人称視点" in sys_inst
    assert "【🚨自己評価フィードバックパッチ】" in sys_inst
    assert "テンポを速めること" in sys_inst


def test_writing_generation_context_minimal():
    """最小設定時の sys_inst 構築検証。"""
    ctx = WritingGenerationContext(sys_inst="基本指示")
    assert ctx.build_sys_inst() == "基本指示"
