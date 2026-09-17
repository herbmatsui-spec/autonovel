import pytest
from src.services.auditors.rule_based_metrics import (
    calculate_sentence_rhythm,
    calculate_dialogue_ratio,
    calculate_kanji_ratio,
    detect_ai_cliches,
    evaluate_cliffhanger_ending,
    verify_character_suffixes,
)

def test_rule_based_metrics_comprehensive():
    sample = "主人公は歩いた。目の前には広大な城。「止まれ！」と兵士が叫んだ。その時、空が割れた！？"
    rhythm = calculate_sentence_rhythm(sample)
    assert rhythm.sentence_count >= 3
    assert 0.0 <= rhythm.score <= 100.0

    dialogue = calculate_dialogue_ratio(sample)
    assert dialogue.ratio > 0.0

    kanji = calculate_kanji_ratio(sample)
    assert 0.1 <= kanji <= 0.6

    cliches = detect_ai_cliches(sample)
    assert isinstance(cliches, list)

    cliff = evaluate_cliffhanger_ending(sample)
    assert cliff >= 70.0  # 末尾に！？があるため高得点

def test_character_suffix_verification():
    dialogues = ["わたくしが参りますわ", "ごきげんようですわ"]
    score = verify_character_suffixes(dialogues, [r"ですわ$", r"ますわ$"])
    assert score == 100.0

    broken_dialogues = ["俺が行くぜ", "ごきげんようですわ"]
    broken_score = verify_character_suffixes(broken_dialogues, [r"ですわ$", r"ますわ$"])
    assert broken_score == 50.0
