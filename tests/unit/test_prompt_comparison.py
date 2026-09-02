from src.services.prompt_comparison import decide_winner, weighted_total


def test_weighted_total_calculation():
    """スコアの重み付け合計計算の検証。"""
    scores = {
        "hook_retention": 1.0,
        "pacing": 0.8,
        "character_consistency": 0.9,
        "commercial_viability": 1.0,
        "emotional_resonance": 0.7,
        "coherence": 0.85,
    }

    total = weighted_total(scores)
    assert 0.8 <= total <= 1.0


def test_decide_winner_selects_highest_score():
    """複数バージョンの結果から最高スコアの勝者が正しく選定されることの検証。"""
    results = [
        {"version_id": "v1.0", "label": "Version 1.0", "weighted_total": 0.75, "scores": {}},
        {"version_id": "v1.1", "label": "Version 1.1", "weighted_total": 0.92, "scores": {}},
        {"version_id": "v2.0", "label": "Version 2.0", "weighted_total": 0.81, "scores": {}},
    ]

    winner = decide_winner(results)
    assert winner["winner_id"] == "v1.1"
    assert winner["winner_label"] == "Version 1.1"
    assert winner["reason"] == "最高合計スコア"


def test_decide_winner_empty_results():
    """結果が空の場合の安全なハンドリング検証。"""
    winner = decide_winner([])
    assert winner["winner_id"] is None
