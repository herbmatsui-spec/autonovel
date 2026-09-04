"""テストデータファクトリ.
 
このモジュールは、統合テストで使用するテストデータを生成するための
ファクトリ関数を提供します。
"""
from __future__ import annotations

import random
import string
from datetime import datetime, timedelta
from typing import Dict, Any, Optional


def random_string(length: int = 8) -> str:
    """ランダムな文字列を生成."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def random_email() -> str:
    """ランダムなメールアドレスを生成."""
    return f"{random_string()}@{random_string()}.com"


def random_name() -> str:
    """ランダムな名前を生成."""
    first_names = ["太郎", "花子", "次郎", "三郎", "健太", "美咲", "裕太", "さくら"]
    last_names = ["佐藤", "鈴木", "高橋", "田中", "渡辺", "伊藤", "山本", "中村"]
    return f"{random.choice(last_names)}{random.choice(first_names)}"


def user_factory(**kwargs) -> Dict[str, Any]:
    """ユーザーオブジェクトのファクトリ.
    
    Args:
        **kwargs: 上書きするフィールド
        
    Returns:
        ユーザーデータの辞書
    """
    defaults = {
        "id": random.randint(1, 10000),
        "username": random_string(),
        "email": random_email(),
        "full_name": random_name(),
        "is_active": True,
        "created_at": datetime.now() - timedelta(days=random.randint(0, 365)),
        "updated_at": datetime.now()
    }
    defaults.update(kwargs)
    return defaults


def book_factory(**kwargs) -> Dict[str, Any]:
    """書籍オブジェクトのファクトリ.
    
    Args:
        **kwargs: 上書きするフィールド
        
    Returns:
        書籍データの辞書
    """
    defaults = {
        "id": random.randint(1, 1000),
        "title": f"{random_string(5)}の物語",
        "author": random_name(),
        "genre": random.choice(["ファンタジー", "SF", "ミステリー", "恋愛", "歴史"]),
        "publication_year": random.randint(1950, 2023),
        "isbn": f"{random.randint(100, 999)}-{random.randint(1000, 9999)}-{random.randint(100, 999)}-{random.randint(1000, 9999)}-{random.randint(0, 9)}",
        "page_count": random.randint(100, 1000),
        "language": random.choice(["日本語", "英語", "フランス語", "ドイツ語"]),
        "created_at": datetime.now() - timedelta(days=random.randint(0, 365)),
        "updated_at": datetime.now()
    }
    defaults.update(kwargs)
    return defaults


def chapter_factory(**kwargs) -> Dict[str, Any]:
    """章オブジェクトのファクトリ.
    
    Args:
        **kwargs: 上書きするフィールド
        
    Returns:
        章データの辞書
    """
    # チャプタ番号を決定（指定されていればそれを使い、なければランダム）
    chapter_number = kwargs.get("chapter_number", random.randint(1, 50))
    
    defaults = {
        "id": random.randint(1, 10000),
        "book_id": kwargs.get("book_id", random.randint(1, 1000)),
        "chapter_number": chapter_number,
        "title": f"第{chapter_number}章",
        "content": "これはサンプルの章内容です。" * random.randint(10, 50),
        "word_count": random.randint(500, 5000),
        "created_at": datetime.now() - timedelta(days=random.randint(0, 365)),
        "updated_at": datetime.now()
    }
    defaults.update(kwargs)
    return defaults


def character_factory(**kwargs) -> Dict[str, Any]:
    """キャラクター情報のファクトリ.
    
    Args:
        **kwargs: 上書きするフィールド
        
    Returns:
        キャラクターデータの辞書
    """
    defaults = {
        "id": random.randint(1, 10000),
        "book_id": kwargs.get("book_id", random.randint(1, 1000)),
        "name": random_name(),
        "role": random.choice(["主人公", "ヒロイン", "ライバル", "メンター", "悪役", "サポート"]),
        "description": f"{random_name()}は物語の中で重要な役割を果たします。",
        "first_appearance_chapter": random.randint(1, 10),
        "created_at": datetime.now() - timedelta(days=random.randint(0, 365)),
        "updated_at": datetime.now()
    }
    defaults.update(kwargs)
    return defaults


def factory_book(**kwargs) -> Dict[str, Any]:
    """書籍ファクトリのエイリアス（命名の統一のため）."""
    return book_factory(**kwargs)


def factory_character(**kwargs) -> Dict[str, Any]:
    """キャラクター情報ファクトリのエイリアス."""
    return character_factory(**kwargs)


def factory_chapter(**kwargs) -> Dict[str, Any]:
    """章ファクトリのエイリアス."""
    return chapter_factory(**kwargs)


def factory_user(**kwargs) -> Dict[str, Any]:
    """ユーザーファクトリのエイリアス."""
    return user_factory(**kwargs)