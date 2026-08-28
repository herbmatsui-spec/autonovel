"""
tests/unit/test_affinity_tracker.py - Phase 1: AffinityTracker FSM and Multidimensional Model Tests
"""

import pytest
from src.schemas.ux_schemas import AffinityData
from src.services.affinity_tracker import AffinityTracker


def test_affinity_tracker_calculate_mood():
    """ステップ 10 & 11: _calculate_mood の各分岐テスト"""
    tracker = AffinityTracker(initial_characters=[])

    # 1. 警戒状態 (wariness >= 60)
    wary_data = AffinityData(character_name="テスト", affinity_score=70.0, wariness_score=65.0)
    assert tracker._calculate_mood(wary_data) == "wary"

    # 2. 熱烈・深い愛 (aff >= 80, dep >= 60, wary < 60)
    deep_data = AffinityData(character_name="テスト", affinity_score=85.0, dependency_score=70.0, wariness_score=10.0)
    assert tracker._calculate_mood(deep_data) == "deep_love"

    # 3. ツンデレ (aff >= 50, wary >= 35)
    tsun_data = AffinityData(character_name="テスト", affinity_score=55.0, wariness_score=40.0)
    assert tracker._calculate_mood(tsun_data) == "tsundere"

    # 4. 好意的 (aff >= 60, trust >= 50, wary < 35)
    aff_data = AffinityData(character_name="テスト", affinity_score=65.0, trust_score=55.0, wariness_score=20.0)
    assert tracker._calculate_mood(aff_data) == "affectionate"

    # 5. 観察 (trust >= 40 or aff >= 40)
    obs_data = AffinityData(character_name="テスト", affinity_score=45.0, trust_score=40.0, wariness_score=20.0)
    assert tracker._calculate_mood(obs_data) == "observation"


def test_affinity_tracker_dynamic_initialization():
    """ステップ 12: 任意のキャラクター一覧での動的初期化"""
    chars = ["エリス", "シルフィ", "ロキシー"]
    tracker = AffinityTracker(initial_characters=chars)

    affinities = tracker.get_all_affinities()
    assert len(affinities) == 3
    names = {a.character_name for a in affinities}
    assert names == set(chars)

    eris = tracker.get_affinity("エリス")
    assert eris is not None
    assert eris.affinity_score == 50.0
    assert eris.trust_score == 50.0


def test_affinity_tracker_update_from_text():
    """ステップ 13〜17: テキスト解析によるパラメータ更新とFSM遷移"""
    tracker = AffinityTracker(initial_characters=["アリス"])
    
    # 信頼と好意を高めるテキスト
    positive_text = "ありがとう、あなたと一緒に戦えて本当に嬉しい。信じるよ、相棒！"
    results = tracker.update_from_text(positive_text, character_name="アリス")
    
    alice = tracker.get_affinity("アリス")
    assert alice.affinity_score > 50.0
    assert alice.trust_score > 50.0
    assert alice.wariness_score < 30.0
    assert alice.current_mood in ["affectionate", "deep_love", "observation"]

    # 警戒と嫌悪が高まるテキスト
    negative_text = "怪しい奴め、信用できない。裏切り者、近寄るな！"
    tracker.update_from_text(negative_text, character_name="アリス")
    alice_updated = tracker.get_affinity("アリス")
    assert alice_updated.wariness_score > alice.wariness_score
    assert alice_updated.affinity_score < alice.affinity_score
