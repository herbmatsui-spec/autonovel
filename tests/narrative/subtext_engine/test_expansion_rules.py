"""
Unit tests for Extension Rules 8-15 (Step 14).
"""

import pytest
from src.narrative.subtext_engine.models import DialogueBlock
from src.narrative.subtext_engine.rules import create_extension_rules


def test_extension_rules_coverage():
    rules = {r.id: r for r in create_extension_rules()}
    assert len(rules) == 8

    # Rule 8: Apology deflection
    res8 = rules["rule_08_apology_deflection"].apply(
        DialogueBlock(speaker="A", lines=["「ごめんなさい」"])
    )
    assert res8.modified is True
    assert "謝られても" in res8.block.lines[0]

    # Rule 9: Hesitation breath
    res9 = rules["rule_09_hesitation_stutter"].apply(
        DialogueBlock(speaker="B", lines=["「あっ、あっ」"])
    )
    assert res9.modified is True
    assert "息を詰まらせ" in res9.block.lines[0]

    # Rule 10: Secretive whisper
    res10 = rules["rule_10_secretive_whisper"].apply(
        DialogueBlock(speaker="C", lines=["「ここだけの話だけど」"])
    )
    assert res10.modified is True
    assert "壁に耳があるわ" in res10.block.lines[0]

    # Rule 11: Rhetorical evasion
    res11 = rules["rule_11_rhetorical_evasion"].apply(
        DialogueBlock(speaker="D", lines=["「どうしてそんなことを聞くの？」"])
    )
    assert res11.modified is True
    assert "どうするつもり？" in res11.block.lines[0]

    # Rule 12: Condescending politeness
    res12 = rules["rule_12_condescending_politeness"].apply(
        DialogueBlock(speaker="E", lines=["「ご親切にどうも」"])
    )
    assert res12.modified is True
    assert "感服いたしますわ" in res12.block.lines[0]

    # Rule 13: Gaze aversion
    res13 = rules["rule_13_gaze_aversion"].apply(
        DialogueBlock(speaker="F", lines=["「見ないでよ！」"])
    )
    assert res13.modified is True
    assert "咄嗟に顔を背け" in res13.block.lines[0]

    # Rule 14: Monologue cutoff
    res14 = rules["rule_14_monologue_cutoff"].apply(
        DialogueBlock(speaker="G", lines=["「独り言さ」"])
    )
    assert res14.modified is True
    assert "忘れて" in res14.block.lines[0]

    # Rule 15: Unspoken tension
    res15 = rules["rule_15_unspoken_tension"].apply(
        DialogueBlock(speaker="H", lines=["「言いたいことはそれだけか？」"])
    )
    assert res15.modified is True
    assert "お互いのためにならない" in res15.block.lines[0]
