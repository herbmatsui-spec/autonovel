from src.services.amplifier_router import AmplifierType, detect_amplifier_type


def test_detect_amplifier_type():
    # Test CATHARSIS overrides
    assert detect_amplifier_type(is_catharsis=True) == AmplifierType.CATHARSIS
    assert detect_amplifier_type(beat_type="結末") == AmplifierType.CATHARSIS

    # Test mapping by beat_type
    assert detect_amplifier_type(beat_type="具体的行動") == AmplifierType.COMBAT
    assert detect_amplifier_type(beat_type="内面葛藤") == AmplifierType.PSYCHOLOGY
    assert detect_amplifier_type(beat_type="状況") == AmplifierType.SCENERY
    assert detect_amplifier_type(beat_type="余韻") == AmplifierType.SCENERY

    # Test fallback mapping by description
    assert detect_amplifier_type(action_description="魔力が迸る戦闘") == AmplifierType.COMBAT
    assert detect_amplifier_type(action_description="敵の傲慢さと内的葛藤") == AmplifierType.PSYCHOLOGY
    assert detect_amplifier_type(action_description="美味しい食事と日常") == AmplifierType.SCENERY
    assert detect_amplifier_type(action_description="圧倒的ざまぁ逆転劇") == AmplifierType.CATHARSIS

    # Test mapping by catharsis_type
    assert detect_amplifier_type(catharsis_type="ざまぁ") == AmplifierType.CATHARSIS
    assert detect_amplifier_type(catharsis_type="戦闘") == AmplifierType.COMBAT
