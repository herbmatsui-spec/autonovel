from __future__ import annotations

import pytest

from src.services.audio.emotion_classifier import (
    SpeechEmotion,
    AcousticParameters,
    EMOTION_ACOUSTIC_TABLE,
    DialogueEmotionClassifier,
)
from src.services.audio.speaker_mapper import (
    VOICEVOX_STYLE_REGISTRY,
    resolve_speaker_and_style,
    load_voice_config,
    get_speaker_config,
)


def test_speech_emotion_enum():
    assert SpeechEmotion.NEUTRAL == "neutral"
    assert SpeechEmotion.JOY == "joy"
    assert SpeechEmotion.ANGER == "anger"
    assert SpeechEmotion.SADNESS == "sadness"
    assert SpeechEmotion.FEAR == "fear"
    assert SpeechEmotion.SURPRISE == "surprise"
    assert SpeechEmotion.WHISPER == "whisper"
    assert SpeechEmotion.SHOUT == "shout"


def test_acoustic_parameters_defaults():
    params = AcousticParameters()
    assert params.speed_scale == 1.0
    assert params.pitch_scale == 0.0
    assert params.intonation_scale == 1.0
    assert params.volume_scale == 1.0
    assert params.pause_after_sec == 0.4


def test_emotion_acoustic_table_completeness():
    """All emotions should have acoustic parameters defined."""
    for emotion in SpeechEmotion:
        assert emotion in EMOTION_ACOUSTIC_TABLE
        params = EMOTION_ACOUSTIC_TABLE[emotion]
        assert isinstance(params, AcousticParameters)
        assert 0.5 <= params.speed_scale <= 2.0
        assert -0.15 <= params.pitch_scale <= 0.15
        assert 0.0 <= params.intonation_scale <= 2.0
        assert 0.0 <= params.volume_scale <= 2.0
        assert params.pause_after_sec > 0


def test_anger_parameters():
    """Anger should have high speed, high pitch, high intonation, high volume."""
    params = EMOTION_ACOUSTIC_TABLE[SpeechEmotion.ANGER]
    assert params.speed_scale > 1.0
    assert params.pitch_scale > 0.0
    assert params.intonation_scale > 1.0
    assert params.volume_scale > 1.0
    assert params.pause_after_sec < 0.4


def test_whisper_parameters():
    """Whisper should have low speed, low pitch, low intonation, low volume."""
    params = EMOTION_ACOUSTIC_TABLE[SpeechEmotion.WHISPER]
    assert params.speed_scale < 1.0
    assert params.pitch_scale < 0.0
    assert params.intonation_scale < 1.0
    assert params.volume_scale < 1.0


def test_joy_parameters():
    """Joy should have slightly higher speed and pitch."""
    params = EMOTION_ACOUSTIC_TABLE[SpeechEmotion.JOY]
    assert params.speed_scale > 1.0
    assert params.pitch_scale > 0.0
    assert params.intonation_scale > 1.0


def test_sadness_parameters():
    """Sadness should have lower speed, pitch, intonation, volume."""
    params = EMOTION_ACOUSTIC_TABLE[SpeechEmotion.SADNESS]
    assert params.speed_scale < 1.0
    assert params.pitch_scale < 0.0
    assert params.intonation_scale < 1.0
    assert params.volume_scale < 1.0
    assert params.pause_after_sec > 0.4


def test_classifier_anger():
    classifier = DialogueEmotionClassifier()
    
    # Explicit anger keywords (Japanese)
    assert classifier.classify("ふざけるな！") == SpeechEmotion.ANGER
    assert classifier.classify("許さない！絶対に！") == SpeechEmotion.ANGER
    assert classifier.classify("殺してやる！") == SpeechEmotion.ANGER
    assert classifier.classify("ムカつく！") == SpeechEmotion.ANGER
    
    # Multiple exclamation marks with anger keywords
    assert classifier.classify("許さない！！！") == SpeechEmotion.ANGER


def test_classifier_joy():
    classifier = DialogueEmotionClassifier()
    
    assert classifier.classify("わははは！") == SpeechEmotion.JOY
    assert classifier.classify("うれしい！やった！") == SpeechEmotion.JOY
    assert classifier.classify("最高だね！") == SpeechEmotion.JOY
    assert classifier.classify("楽しい！") == SpeechEmotion.JOY


def test_classifier_sadness():
    classifier = DialogueEmotionClassifier()
    
    assert classifier.classify("悲しい…") == SpeechEmotion.SADNESS
    assert classifier.classify("泣きたい…") == SpeechEmotion.SADNESS
    assert classifier.classify("辛い。。") == SpeechEmotion.SADNESS
    assert classifier.classify("寂しい。。") == SpeechEmotion.SADNESS


def test_classifier_fear():
    classifier = DialogueEmotionClassifier()
    
    assert classifier.classify("怖い！") == SpeechEmotion.FEAR
    assert classifier.classify("怯える…") == SpeechEmotion.FEAR
    assert classifier.classify("逃げろ！") == SpeechEmotion.FEAR


def test_classifier_surprise():
    classifier = DialogueEmotionClassifier()
    
    assert classifier.classify("えっ！？") == SpeechEmotion.SURPRISE
    assert classifier.classify("まさか！") == SpeechEmotion.SURPRISE
    assert classifier.classify("本当！？") == SpeechEmotion.SURPRISE
    assert classifier.classify("信じられない！") == SpeechEmotion.SURPRISE


def test_classifier_whisper():
    classifier = DialogueEmotionClassifier()
    
    assert classifier.classify("内緒だよ…") == SpeechEmotion.WHISPER
    assert classifier.classify("ひそひそ…") == SpeechEmotion.WHISPER
    assert classifier.classify("秘密だよ。。") == SpeechEmotion.WHISPER


def test_classifier_shout():
    classifier = DialogueEmotionClassifier()
    
    assert classifier.classify("行くぞ！！！") == SpeechEmotion.SHOUT
    assert classifier.classify("負けるな！！！") == SpeechEmotion.SHOUT
    assert classifier.classify("立ち上がれ！！！") == SpeechEmotion.SHOUT


def test_classifier_neutral():
    classifier = DialogueEmotionClassifier()
    
    assert classifier.classify("今日は良い天気ですね。") == SpeechEmotion.NEUTRAL
    assert classifier.classify("そうですか。") == SpeechEmotion.NEUTRAL
    assert classifier.classify("わかりました。") == SpeechEmotion.NEUTRAL


def test_classifier_context():
    classifier = DialogueEmotionClassifier()
    
    # Context can influence classification
    assert classifier.classify("行くぞ", context="戦闘シーン") == SpeechEmotion.SHOUT


def test_adjust_acoustics_by_punctuation():
    classifier = DialogueEmotionClassifier()
    base_params = AcousticParameters(
        speed_scale=1.0,
        pitch_scale=0.0,
        intonation_scale=1.0,
        volume_scale=1.0,
        pause_after_sec=0.4,
    )
    
    # Three exclamation marks
    adjusted = classifier.adjust_acoustics_by_punctuation(base_params, "行くぞ！！！")
    assert adjusted.speed_scale == 1.1
    assert adjusted.volume_scale == 1.1
    assert adjusted.intonation_scale == 1.1
    
    # Two exclamation marks
    adjusted = classifier.adjust_acoustics_by_punctuation(base_params, "行くぞ！！")
    assert adjusted.speed_scale == 1.05
    assert adjusted.volume_scale == 1.05
    
    # Question mark
    adjusted = classifier.adjust_acoustics_by_punctuation(base_params, "どこへ行くの？")
    assert adjusted.pitch_scale == 0.03
    assert adjusted.intonation_scale == 1.1
    
    # Ellipsis
    adjusted = classifier.adjust_acoustics_by_punctuation(base_params, "悲しい…")
    assert adjusted.pause_after_sec == 0.7
    assert adjusted.speed_scale == 0.9


def test_style_registry_completeness():
    """Check that major speakers have style registrations."""
    assert "ずんだもん" in VOICEVOX_STYLE_REGISTRY
    assert "四国めたん" in VOICEVOX_STYLE_REGISTRY
    assert "春日部つむぎ" in VOICEVOX_STYLE_REGISTRY
    assert "玄野武宏" in VOICEVOX_STYLE_REGISTRY
    
    # Each speaker should have at least NEUTRAL style
    for speaker, styles in VOICEVOX_STYLE_REGISTRY.items():
        assert SpeechEmotion.NEUTRAL in styles
        assert isinstance(styles[SpeechEmotion.NEUTRAL], int)


def test_resolve_speaker_and_style_zundamon():
    speaker_id, params = resolve_speaker_and_style("ずんだもん", SpeechEmotion.NEUTRAL)
    assert speaker_id == 3
    assert params.speed_scale == 1.0
    
    speaker_id, params = resolve_speaker_and_style("ずんだもん", SpeechEmotion.JOY)
    assert speaker_id == 1
    
    speaker_id, params = resolve_speaker_and_style("ずんだもん", SpeechEmotion.ANGER)
    assert speaker_id == 7
    
    speaker_id, params = resolve_speaker_and_style("ずんだもん", SpeechEmotion.WHISPER)
    assert speaker_id == 22


def test_resolve_speaker_and_style_metan():
    speaker_id, params = resolve_speaker_and_style("四国めたん", SpeechEmotion.NEUTRAL)
    assert speaker_id == 2
    
    speaker_id, params = resolve_speaker_and_style("四国めたん", SpeechEmotion.ANGER)
    assert speaker_id == 6


def test_resolve_speaker_and_style_male():
    """Male speakers should resolve correctly."""
    speaker_id, params = resolve_speaker_and_style("玄野武宏", SpeechEmotion.NEUTRAL, gender="male")
    assert speaker_id == 23
    
    speaker_id, params = resolve_speaker_and_style("青山龍星", SpeechEmotion.ANGER, gender="male")
    assert speaker_id == 35


def test_resolve_speaker_and_style_unknown_speaker():
    """Unknown speakers should get default based on gender/role."""
    # Female heroine default
    speaker_id, params = resolve_speaker_and_style("Unknown Character", SpeechEmotion.NEUTRAL)
    assert speaker_id == 3  # Zundamon
    
    # Male hero default
    speaker_id, params = resolve_speaker_and_style("Unknown Male", SpeechEmotion.NEUTRAL, gender="male")
    assert speaker_id == 23  # Genno Takehiro
    
    # Male villain default
    speaker_id, params = resolve_speaker_and_style("Villain", SpeechEmotion.ANGER, gender="male", role="villain")
    assert speaker_id == 28  # Aoyama Ryusei
    
    # Female villain default
    speaker_id, params = resolve_speaker_and_style("Villainess", SpeechEmotion.ANGER, gender="female", role="villain")
    assert speaker_id == 38  # Meimei Himari


def test_resolve_speaker_emotion_fallback():
    """If specific emotion style not found, fallback to NEUTRAL."""
    # Register a speaker with only NEUTRAL
    VOICEVOX_STYLE_REGISTRY["Test Speaker"] = {SpeechEmotion.NEUTRAL: 999}
    
    speaker_id, params = resolve_speaker_and_style("Test Speaker", SpeechEmotion.JOY)
    assert speaker_id == 999  # Falls back to NEUTRAL


def test_load_voice_config_nonexistent():
    """Loading non-existent config should return empty dict."""
    result = load_voice_config("/nonexistent/path.yaml")
    assert result == {}


def test_get_speaker_config():
    config = get_speaker_config("ずんだもん")
    assert config.name == "ずんだもん"
    assert config.gender == "female"
    assert config.role == "heroine"
    
    config = get_speaker_config("玄野武宏")
    assert config.gender == "male"
    assert config.role == "hero"
    
    config = get_speaker_config("冥鳴ひまり")
    assert config.role == "villain"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])