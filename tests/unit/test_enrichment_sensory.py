# tests/unit/test_enrichment_sensory.py
"""EnrichmentAgent 感覚拡充の単体テスト"""
import pytest
from src.agents.enrichment.sensory import (
    detect_abstract_emotions,
    generate_sensory_details,
    replace_with_sensory_expansion,
    expand_sensory_details_pipeline,
    EMOTION_TO_SENSORY_MAP,
    EmotionSpan,
)


class TestEmotionDetection:
    """感情検出のテスト"""

    def test_detect_sadness(self):
        """悲しみ検出"""
        text = "彼は悲しかった。涙が出た。"
        spans = detect_abstract_emotions(text)
        sadness_spans = [s for s in spans if s.emotion == "sadness"]
        assert len(sadness_spans) >= 1
        assert "悲しかった" in sadness_spans[0].abstract_phrase

    def test_detect_anger(self):
        """怒り検出"""
        text = "怒りが込み上げた。腹が立つ。"
        spans = detect_abstract_emotions(text)
        anger_spans = [s for s in spans if s.emotion == "anger"]
        assert len(anger_spans) >= 1

    def test_detect_fear(self):
        """恐怖検出"""
        text = "恐怖で震えた。怖くて逃げ出したい。"
        spans = detect_abstract_emotions(text)
        fear_spans = [s for s in spans if s.emotion == "fear"]
        assert len(fear_spans) >= 1

    def test_detect_joy(self):
        """喜び検出"""
        text = "嬉しくて笑顔になった。最高だ。"
        spans = detect_abstract_emotions(text)
        joy_spans = [s for s in spans if s.emotion == "joy"]
        assert len(joy_spans) >= 1

    def test_detect_surprise(self):
        """驚き検出"""
        text = "驚いて目を見開いた。信じられない。"
        spans = detect_abstract_emotions(text)
        surprise_spans = [s for s in spans if s.emotion == "surprise"]
        assert len(surprise_spans) >= 1

    def test_detect_disgust(self):
        """嫌悪検出"""
        text = "嫌悪感を抱いた。吐き気がする。"
        spans = detect_abstract_emotions(text)
        disgust_spans = [s for s in spans if s.emotion == "disgust"]
        assert len(disgust_spans) >= 1

    def test_no_overlap(self):
        """重複検出なし"""
        text = "悲しかった。悲しみが胸をよぎった。"
        spans = detect_abstract_emotions(text)
        # 近い位置の重複は除外される
        positions = [(s.start, s.end) for s in spans]
        for i, (s1, e1) in enumerate(positions):
            for j, (s2, e2) in enumerate(positions):
                if i != j:
                    assert not (s1 < e2 and s2 < e1)  # 重複なし


class TestSensoryMap:
    """感覚マッピングのテスト"""

    def test_all_emotions_covered(self):
        """6基本感情すべてカバー"""
        expected_emotions = {"sadness", "anger", "fear", "joy", "surprise", "disgust"}
        assert set(EMOTION_TO_SENSORY_MAP.keys()) == expected_emotions

    def test_all_senses_per_emotion(self):
        """各感情に5感覚以上"""
        for emotion, senses in EMOTION_TO_SENSORY_MAP.items():
            assert len(senses) >= 3  # 少なくとも3感覚
            for sense in ["visual", "auditory", "tactile", "olfactory", "gustatory"]:
                if sense in senses:
                    assert len(senses[sense]) >= 1


class TestSensoryGeneration:
    """感覚詳細生成のテスト"""

    def test_generate_sensory_details(self):
        """感覚詳細生成"""
        span = EmotionSpan(
            start=0, end=5, emotion="sadness", intensity=0.8, abstract_phrase="悲しかった"
        )
        details = generate_sensory_details(span, "雨の夜、独り佇んでいた", "third_person")
        assert len(details) >= 2
        assert len(details) <= 3
        # 感覚タグ付き
        for d in details:
            assert d.startswith("[") and "]" in d

    def test_generate_sensory_details_context_aware(self):
        """文脈対応感覚選択"""
        span = EmotionSpan(0, 5, "sadness", 0.8, "悲しかった")
        # 雨の文脈 -> tactile, auditory, olfactory 優先
        details = generate_sensory_details(span, "雨が降る夜だった", "third_person")
        sense_tags = [d.split("]")[0].strip("[") for d in details]
        assert "tactile" in sense_tags or "auditory" in sense_tags


class TestReplacement:
    """置換のテスト"""

    def test_replace_with_sensory_expansion(self):
        """感覚展開置換"""
        text = "彼は悲しかった。怒りが込み上げた。"
        spans = [
            EmotionSpan(3, 8, "sadness", 0.7, "悲しかった"),
            EmotionSpan(10, 17, "anger", 0.8, "怒りが込み上げた"),
        ]
        details_list = [
            ["[visual] 涙がこぼれた", "[tactile] 頬が濡れた"],
            ["[visual] 顔が赤くなった", "[auditory] 低く唸った"],
        ]
        enriched, meta = replace_with_sensory_expansion(text, spans, details_list)
        assert "涙がこぼれた" in enriched
        assert "顔が赤くなった" in enriched
        assert len(meta) == 2
        assert meta[0]["emotion"] == "sadness"
        assert meta[1]["emotion"] == "anger"

    def test_expand_sensory_details_pipeline(self):
        """パイプライン統合テスト"""
        text = "彼は悲しかった。戦いの後だった。"
        enriched, meta = expand_sensory_details_pipeline(
            text, scene_context="雨の戦場", pov="third_person"
        )
        assert len(enriched) > len(text)  # 展開で長くなる
        assert len(meta) >= 1
        for m in meta:
            assert "original_phrase" in m
            assert "expanded_text" in m
            assert "emotion" in m
            assert "senses_covered" in m