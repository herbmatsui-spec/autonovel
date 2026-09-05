import pytest
from src.services.foreshadowing_id_generator import (
    generate_foreshadowing_id,
    generate_foreshadowing_id_with_sequence,
    GENRE_CODES
)


def test_generate_foreshadowing_id_basic():
    """基本的な伏線ID生成のテスト"""
    # ファンタジー、第1巻第3話
    fid = generate_foreshadowing_id("ファンタジー", 1, 3)
    assert fid == "F-FAN-001-003-001"
    
    # 異世界転生、第5巻第12話
    fid = generate_foreshadowing_id("異世界転生", 5, 12)
    assert fid == "F-ISE-005-012-001"
    
    # SF、第10巻第1話
    fid = generate_foreshadowing_id("SF", 10, 1)
    assert fid == "F-SF-010-001-001"


def test_generate_foreshadowing_id_unknown_genre():
    """不明なジャンルの場合の伏線ID生成のテスト"""
    fid = generate_foreshadowing_id("未知のジャンル", 1, 1)
    assert fid == "F-OTH-001-001-001"


def test_generate_foreshadowing_id_zero_padding():
    """ゼロパディングのテスト"""
    fid = generate_foreshadowing_id("ファンタジー", 1, 1)
    assert fid == "F-FAN-001-001-001"
    
    fid = generate_foreshadowing_id("ファンタジー", 12, 3)
    assert fid == "F-FAN-012-003-001"
    
    fid = generate_foreshadowing_id("ファンタジー", 123, 45)
    assert fid == "F-FAN-123-045-001"


def test_generate_foreshadowing_id_with_sequence():
    """連番を指定した伏線ID生成のテスト"""
    # デフォルトの連番（001）
    fid = generate_foreshadowing_id_with_sequence("ファンタジー", 1, 3, 0)
    assert fid == "F-FAN-001-003-000"
    
    fid = generate_foreshadowing_id_with_sequence("ファンタジー", 1, 3, 1)
    assert fid == "F-FAN-001-003-001"
    
    fid = generate_foreshadowing_id_with_sequence("ファンタジー", 1, 3, 12)
    assert fid == "F-FAN-001-003-012"
    
    fid = generate_foreshadowing_id_with_sequence("ファンタジー", 1, 3, 123)
    assert fid == "F-FAN-001-003-123"


def test_generate_foreshadowing_id_with_sequence_negative():
    """負の連番の場合のエラーテスト"""
    with pytest.raises(ValueError, match="Sequence must be non-negative"):
        generate_foreshadowing_id_with_sequence("ファンタジー", 1, 1, -1)


def test_genre_codes():
    """ジャンルコード辞書のテスト"""
    assert GENRE_CODES["ファンタジー"] == "FAN"
    assert GENRE_CODES["学園ラブコメ"] == "GAK"
    assert GENRE_CODES["異世界転生"] == "ISE"
    assert GENRE_CODES["SF"] == "SF"
    assert GENRE_CODES["ホラー"] == "HOR"
    assert GENRE_CODES["ミステリー"] == "MIS"
    assert GENRE_CODES["恋愛"] == "REN"
    assert GENRE_CODES["歴史"] == "REK"
    assert GENRE_CODES["スポーツ"] == "SPO"
    assert GENRE_CODES["コメディ"] == "COM"


def test_genre_codes_unknown():
    """不明なジャンルのデフォルト値テスト"""
    # 実際の関数では .get() メソッドを使っているため、
    # 辞書にないキーはデフォルト値 "OTH" が返される
    assert "未知のジャンル" not in GENRE_CODES
    # これは generate_foreshadowing_id 関数内で処理される