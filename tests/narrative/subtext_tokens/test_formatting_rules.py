"""
Unit tests for DialogueFormatter and post-processing formatting rules (PLAN_Y3 Step 7-14).
"""

import pytest
from src.narrative.subtext_engine.models import SubtextContext
from src.narrative.subtext_tokens.formatter import DialogueFormatter


def test_normalize_punctuation():
    formatter = DialogueFormatter()
    raw = "“こんにちは！！”\n\n\n\n“ありがとう………”"
    norm = formatter.normalize_punctuation(raw)
    assert "「こんにちは！」" in norm
    assert "「ありがとう……」" in norm
    assert "\n\n\n" not in norm


def test_ensure_beat_before_climax():
    formatter = DialogueFormatter()
    raw = "「私の限界だ」"
    res = formatter.ensure_beat_before_climax(raw)
    assert "……限界" in res


def test_compress_explanatory_dialogue():
    formatter = DialogueFormatter()
    raw = "「敵が来た」\n「城門を閉鎖せよ」\n「戦うしかない」"
    res = formatter.compress_explanatory_dialogue(raw)
    assert "（重苦しい沈黙" in res
    assert "「戦うしかない」" in res


def test_balance_dialogue_action_ratio():
    formatter = DialogueFormatter()
    raw = "「台詞1」\n「台詞2」\n「台詞3」\n「台詞4」"
    res = formatter.balance_dialogue_action_ratio(raw, max_dialogue_ratio=0.7)
    # Should insert stage direction beat
    assert "（" in res


def test_merge_consecutive_dialogue():
    formatter = DialogueFormatter()
    raw = "「どうして？」\n「教えてよ」"
    res = formatter.merge_consecutive_dialogue(raw)
    assert res == "「どうして？……教えてよ」"


def test_master_post_process_dialogue_pipeline():
    formatter = DialogueFormatter()
    raw = "「何の話だ」[BEAT:pause:short]「答えてくれ」"
    ctx = SubtextContext(speaker="elena")
    processed = formatter.post_process_dialogue(raw, context=ctx)

    assert "[BEAT:pause:short]" not in processed
    assert len(processed) > 0


def test_token_debugger_generate_html(tmp_path):
    from src.narrative.subtext_tokens.debugger import TokenDebugger

    raw = "「話せ」[BEAT:pause:short]「なぜ黙る」"
    proc = "「話せ」……「なぜ黙る」"
    out_file = tmp_path / "diff.html"
    html_res = TokenDebugger.generate_html_diff(raw, proc, output_path=out_file)

    assert out_file.exists()
    assert "Subtext Token Expansion Diff Report" in html_res
    assert "[BEAT:pause:short]" in html_res
