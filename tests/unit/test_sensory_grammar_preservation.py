"""Unit tests for sensory expansion grammar preservation and syntax safety (Part 3, Step 34)."""
import pytest
from src.agents.enrichment.sensory import (
    EmotionSpan,
    extract_sentence_span,
    detect_trailing_conjunction,
    detect_abstract_emotions,
    is_inside_dialogue,
    sanitize_punctuation,
    validate_rewritten_sentence,
    replace_with_sensory_expansion,
)


def test_sentence_span_extraction_boundary_cases():
    """句読点、感嘆符、疑問符、改行による文境界抽出テスト"""
    # 句点
    _, _, s1 = extract_sentence_span("前の文。彼は悲しかったが耐えた。次の文。", 7, 12)
    assert s1 == "彼は悲しかったが耐えた。"

    # 感嘆符
    _, _, s2 = extract_sentence_span("逃げろ！恐ろしい化け物が迫る！急げ！", 5, 9)
    assert s2 == "恐ろしい化け物が迫る！"

    # 疑問符
    _, _, s3 = extract_sentence_span("誰だ？怒りに震えているのか？答えろ。", 4, 6)
    assert s3 == "怒りに震えているのか？"

    # 改行
    _, _, s4 = extract_sentence_span("段落一。\n絶望が広がる\n段落三。", 6, 8)
    assert s4 == "絶望が広がる"


@pytest.mark.parametrize(
    "conjunction,sample_text",
    [
        ("が、", "彼は悲しかったが、耐えた。"),
        ("が", "彼は悲しかったが耐えた。"),
        ("だが", "怒りだが抑えた。"),
        ("ものの", "恐ろしいものの前進した。"),
        ("ので", "悲しいので涙が出た。"),
        ("なので", "怒りなので手が震えた。"),
        ("から", "悔しいから練習した。"),
        ("ため", "悲しいため声が出ない。"),
        ("ながら", "恐れながら進んだ。"),
        ("でも", "悲しいでも笑った。"),
        ("けれど", "悔しいけれど諦めない。"),
        ("けれども", "悔しいけれども諦めない。"),
    ],
)
def test_detect_trailing_conjunction_patterns(conjunction, sample_text):
    """多様な接続詞・接続助詞パターンの検知テスト"""
    for emotion_word in ["悲しかった", "恐ろしい", "怒り", "悔しい", "悲しい", "恐れ"]:
        if emotion_word in sample_text:
            pos = sample_text.find(emotion_word) + len(emotion_word)
            found = detect_trailing_conjunction(sample_text, pos)
            assert found != "", f"Failed to detect conjunction in '{sample_text}' at pos {pos}"
            assert found in conjunction or conjunction.startswith(found) or found.startswith(conjunction)
            break


def test_dialogue_protection_comprehensive():
    """かぎ括弧（「」および『』）内の感情表現が確実に保護されること"""
    text = (
        "「俺は悔しいんだ！」と叫んだ。\n"
        "『悲しい運命』という本を読んでいた。\n"
        "しかし彼の心には本当の怒りがあった。"
    )
    # 地の文の「怒り」だけが検出され、セリフやタイトル内の「悔しい」「悲しい」はスキップ
    spans = detect_abstract_emotions(text, skip_dialogue=True)
    assert len(spans) == 1
    assert spans[0].emotion == "anger"
    assert "怒り" in spans[0].abstract_phrase


def test_syntax_sanitization_comprehensive():
    """連続記号や不自然な助詞接続が自動サニタイズされること"""
    raw_texts = [
        ("悲しかった。。。静かだった。", "悲しかった。静かだった。"),
        ("冷たい涙、、、頬を伝う。", "冷たい涙、頬を伝う。"),
        ("激怒した。が耐えた。", "激怒したが耐えた。"),
        ("恐ろしい。ものの前進した。", "恐ろしいものの前進した。"),
        ("悲しい。ので涙が出た。", "悲しいので涙が出た。"),
        ("悲しい。、静寂。", "悲しい、静寂。"),
    ]
    for inp, expected in raw_texts:
        assert sanitize_punctuation(inp) == expected


def test_automatic_rollback_on_malformed_llm_output():
    """異常・破損出力時の自動ロールバックテスト"""
    original = "少女は恐怖に震えていたが、必死に走った。"
    spans = detect_abstract_emotions(original)
    assert len(spans) == 1

    # 1. 極端に短い出力
    out_short, _ = replace_with_sensory_expansion(original, spans, [["あ"]])
    assert "少女は恐怖に震えていたが、必死に走った。" in out_short

    # 2. 記号のみ
    out_symbols, _ = replace_with_sensory_expansion(original, spans, [["……？！"]])
    assert "少女は恐怖に震えていたが、必死に走った。" in out_symbols

    # 3. エラー文字列
    out_err, _ = replace_with_sensory_expansion(original, spans, [["Error 500 Connection Timeout"]])
    assert "少女は恐怖に震えていたが、必死に走った。" in out_err
