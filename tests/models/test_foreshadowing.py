import pytest
from src.models.foreshadowing import Foreshadowing


def test_foreshadowing_creation():
    """Foreshadowing オブジェクトの作成テスト"""
    fs = Foreshadowing(
        id="F-001",
        content="主人公の実父母の正体",
        hang_volume=1,
        hang_episode=3,
        hang_chapter=5,
        hang_type="implicit",
        importance="★★★"
    )
    
    assert fs.id == "F-001"
    assert fs.content == "主人公の実父母の正体"
    assert fs.hang_volume == 1
    assert fs.hang_episode == 3
    assert fs.hang_chapter == 5
    assert fs.hang_type == "implicit"
    assert fs.importance == "★★★"
    assert fs.resolution_volume is None
    assert fs.resolution_episode is None


def test_foreshadowing_with_resolution():
    """解決情報付きForeshadowing オブジェクトの作成テスト"""
    fs = Foreshadowing(
        id="F-002",
        content="魔王の弱点",
        hang_volume=2,
        hang_episode=5,
        hang_chapter=2,
        hang_type="explicit",
        importance="★★",
        resolution_volume=5,
        resolution_episode=3
    )
    
    assert fs.resolution_volume == 5
    assert fs.resolution_episode == 3


def test_foreshadowing_to_dict():
    """to_dict メソッドのテスト"""
    fs = Foreshadowing(
        id="F-003",
        content="古い約束",
        hang_volume=3,
        hang_episode=1,
        hang_chapter=10,
        hang_type="reader_task",
        importance="★",
        resolution_volume=4,
        resolution_episode=2
    )
    
    expected = {
        "id": "F-003",
        "content": "古い約束",
        "hang_volume": 3,
        "hang_episode": 1,
        "hang_chapter": 10,
        "hang_type": "reader_task",
        "importance": "★",
        "resolution_volume": 4,
        "resolution_episode": 2
    }
    
    assert fs.to_dict() == expected


def test_foreshadowing_from_dict():
    """from_dict メソッドのテスト"""
    data = {
        "id": "F-004",
        "content": "隠された真実",
        "hang_volume": 1,
        "hang_episode": 1,
        "hang_chapter": 1,
        "hang_type": "explicit",
        "importance": "★★★",
        "resolution_volume": 3,
        "resolution_episode": 4
    }
    
    fs = Foreshadowing.from_dict(data)
    
    assert fs.id == "F-004"
    assert fs.content == "隠された真実"
    assert fs.hang_volume == 1
    assert fs.hang_episode == 1
    assert fs.hang_chapter == 1
    assert fs.hang_type == "explicit"
    assert fs.importance == "★★★"
    assert fs.resolution_volume == 3
    assert fs.resolution_episode == 4


def test_foreshadowing_roundtrip():
    """to_dict -> from_dict のラウンドトリップテスト"""
    original = Foreshadowing(
        id="F-005",
        content="転移魔法陣",
        hang_volume=2,
        hang_episode=4,
        hang_chapter=7,
        hang_type="implicit",
        importance="★★",
        resolution_volume=6,
        resolution_episode=1
    )
    
    data = original.to_dict()
    restored = Foreshadowing.from_dict(data)
    
    assert original == restored