"""
伏線ID生成ユーティリティ
"""

from __future__ import annotations

from typing import Dict


# ジャンルコード辞書（簡易版）
GENRE_CODES: Dict[str, str] = {
    "ファンタジー": "FAN",
    "学園ラブコメ": "GAK",
    "異世界転生": "ISE",
    "SF": "SF",
    "ホラー": "HOR",
    "ミステリー": "MIS",
    "恋愛": "REN",
    "歴史": "REK",
    "スポーツ": "SPO",
    "コメディ": "COM",
}


def generate_foreshadowing_id(genre: str, volume: int, episode: int) -> str:
    """
    伏線IDを生成する
    
    形式: F-{ジャンルコード}-{巻数:03d}-{話数:03d}-{連番:03d}
    
    Args:
        genre: ジャンル名
        volume: 巻数
        episode: 話数
        
    Returns:
        生成された伏線ID
        
    Note:
        この実装では簡易的に、同じ巻話内での連番は1から始まるものとする。
        実際の実装では、データベースから現在の連番を取得する必要がある。
    """
    genre_code = GENRE_CODES.get(genre, "OTH")  # 不明なジャンルは OTH (Other)
    return f"F-{genre_code}-{volume:03d}-{episode:03d}-001"


def generate_foreshadowing_id_with_sequence(genre: str, volume: int, episode: int, sequence: int) -> str:
    """
    連番を指定して伏線IDを生成する
    
    形式: F-{ジャンルコード}-{巻数:03d}-{話数:03d}-{連番:03d}
    
    Args:
        genre: ジャンル名
        volume: 巻数
        episode: 話数
        sequence: 連番（0以上の整数）
        
    Returns:
        生成された伏線ID
    """
    if sequence < 0:
        raise ValueError("Sequence must be non-negative")
        
    genre_code = GENRE_CODES.get(genre, "OTH")
    return f"F-{genre_code}-{volume:03d}-{episode:03d}-{sequence:03d}"