from src.models.plot import DynamicPacing, ReviewLog, SceneBeat, extract_float


def test_extract_float_helper():
    """extract_float ヘルパーの文字列・数値パース検証。"""
    assert extract_float(3.14) == 3.14
    assert extract_float(5) == 5.0
    assert extract_float("85.5%") == 85.5
    assert extract_float("Score: -12.3 points") == -12.3
    assert extract_float(None) == 0.0


def test_review_log_model():
    """ReviewLog モデルのフィールドとバリデーション検証。"""
    log = ReviewLog(
        plan_name="Plan A",
        experiment_1_score=80,
        experiment_1_comments="Good pacing",
    )
    assert log.plan_name == "Plan A"
    assert log.experiment_1_score == 80


def test_dynamic_pacing_model():
    """DynamicPacing モデルのフィールド検証。"""
    pacing = DynamicPacing(
        ep_range="1-3",
        phase_name="起",
        required_events="主人公の覚醒",
    )
    assert pacing.ep_range == "1-3"
    assert pacing.phase_name == "起"


def test_scene_beat_model():
    """SceneBeat モデルの生成検証。"""
    beat = SceneBeat(
        beat_num=1,
        physical_action="剣を抜く",
        sensory_tags=["金属音", "冷気"],
        emotion_phase="緊張",
        word_budget=300,
    )
    assert beat.beat_num == 1
    assert "金属音" in beat.sensory_tags
