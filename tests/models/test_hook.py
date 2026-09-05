import pytest
from src.models.hook import Hook


def test_hook_creation():
    """Hook オブジェクトの作成テスト"""
    hook = Hook(
        id="H-001",
        type="mystery",
        content="なぜ、彼女は俺の名を知っていたのか──",
        target_position="episode_end",
        volume=1,
        episode=3,
        chapter=5
    )
    
    assert hook.id == "H-001"
    assert hook.type == "mystery"
    assert hook.content == "なぜ、彼女は俺の名を知っていたのか──"
    assert hook.target_position == "episode_end"
    assert hook.volume == 1
    assert hook.episode == 3
    assert hook.chapter == 5


def test_hook_all_types():
    """すべてのフックタイプのテスト"""
    # mystery
    hook_mystery = Hook(
        id="H-002",
        type="mystery",
        content="謎のフック",
        target_position="episode_end",
        volume=1,
        episode=1,
        chapter=1
    )
    assert hook_mystery.type == "mystery"
    
    # threat
    hook_threat = Hook(
        id="H-003",
        type="threat",
        content="脅威のフック",
        target_position="episode_end",
        volume=1,
        episode=1,
        chapter=1
    )
    assert hook_threat.type == "threat"
    
    # emotion
    hook_emotion = Hook(
        id="H-004",
        type="emotion",
        content="感情のフック",
        target_position="episode_end",
        volume=1,
        episode=1,
        chapter=1
    )
    assert hook_emotion.type == "emotion"


def test_hook_all_target_positions():
    """すべてのターゲットポジションのテスト"""
    # episode_end
    hook_ep = Hook(
        id="H-005",
        type="mystery",
        content="話終わりフック",
        target_position="episode_end",
        volume=1,
        episode=1,
        chapter=1
    )
    assert hook_ep.target_position == "episode_end"
    
    # volume_end
    hook_vol = Hook(
        id="H-006",
        type="mystery",
        content="巻終わりフック",
        target_position="volume_end",
        volume=1,
        episode=1,
        chapter=1
    )
    assert hook_vol.target_position == "volume_end"
    
    # series_end
    hook_ser = Hook(
        id="H-007",
        type="mystery",
        content="シリーズ終わりフック",
        target_position="series_end",
        volume=1,
        episode=1,
        chapter=1
    )
    assert hook_ser.target_position == "series_end"


def test_hook_to_dict():
    """to_dict メソッドのテスト"""
    hook = Hook(
        id="H-008",
        type="threat",
        content="暗闇に潜む影",
        target_position="volume_end",
        volume=2,
        episode=5,
        chapter=12
    )
    
    expected = {
        "id": "H-008",
        "type": "threat",
        "content": "暗闇に潜む影",
        "target_position": "volume_end",
        "volume": 2,
        "episode": 5,
        "chapter": 12
    }
    
    assert hook.to_dict() == expected


def test_hook_from_dict():
    """from_dict メソッドのテスト"""
    data = {
        "id": "H-009",
        "type": "emotion",
        "content": "二人だけの秘密",
        "target_position": "episode_end",
        "volume": 3,
        "episode": 2,
        "chapter": 7
    }
    
    hook = Hook.from_dict(data)
    
    assert hook.id == "H-009"
    assert hook.type == "emotion"
    assert hook.content == "二人だけの秘密"
    assert hook.target_position == "episode_end"
    assert hook.volume == 3
    assert hook.episode == 2
    assert hook.chapter == 7


def test_hook_roundtrip():
    """to_dict -> from_dict のラウンドトリップテスト"""
    original = Hook(
        id="H-010",
        type="mystery",
        content="第十巻の衝撃真実",
        target_position="volume_end",
        volume=10,
        episode=1,
        chapter=1
    )
    
    data = original.to_dict()
    restored = Hook.from_dict(data)
    
    assert original == restored