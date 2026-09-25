"""
Performance, error handling, multilingual, and sync tests (PLAN_Y3 Step 18, 19, 22, 23).
"""

from pathlib import Path
import pytest
from src.narrative.subtext_engine.models import SubtextContext
from src.narrative.subtext_tokens.expander import TokenExpander
from src.narrative.subtext_tokens.formatter import DialogueFormatter
from scripts.validate_prompt_tokens import validate_prompt_token_sync


def test_token_expansion_performance():
    formatter = DialogueFormatter()
    raw = "「台詞です」[BEAT:pause:short]「次の台詞です」[GLANCE:away]"
    # 500 lines benchmark
    lines = [raw] * 500
    text = "\n".join(lines)

    res = formatter.post_process_dialogue(text, seed=42)
    assert len(res) > 0
    assert "[BEAT:pause:short]" not in res


def test_token_error_handling_unknown_token():
    expander = TokenExpander()
    raw = "「質問です」[BEAT:unknown_key_xyz]「終わりです」"
    # Should safely fallback without raising
    expanded = expander.expand(raw)
    assert "[BEAT:unknown_key_xyz]" not in expanded
    assert "「質問です」" in expanded


def test_multilingual_token_expansion():
    en_expander = TokenExpander(lang="en")
    res_en = en_expander.expand("Hello [BEAT:pause:short] world", seed=42)
    assert "[BEAT:pause:short]" not in res_en

    zh_expander = TokenExpander(lang="zh")
    res_zh = zh_expander.expand("你好 [BEAT:pause:short] 世界", seed=42)
    assert "[BEAT:pause:short]" not in res_zh


def test_prompt_token_synchronization():
    errors = validate_prompt_token_sync()
    assert len(errors) == 0, f"Prompt tokens out of sync with dictionary: {errors}"
