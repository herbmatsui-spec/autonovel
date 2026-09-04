"""ファクトリの使用例を示すテスト.
 
ファクトリを使用してテストデータを生成する方法を示します。
"""
from __future__ import annotations

import pytest
from datetime import datetime
from tests.factories import user_factory, book_factory, character_factory, chapter_factory


def test_user_factory():
    """ユーザーファクトリが正しく動作することを確認するテスト."""
    user = user_factory()
    assert "id" in user
    assert "username" in user
    assert "email" in user
    assert "full_name" in user
    assert isinstance(user["is_active"], bool)
    assert isinstance(user["created_at"], datetime)
    assert isinstance(user["updated_at"], datetime)
    
    # 値の範囲をチェック
    assert 1 <= user["id"] <= 10000
    assert isinstance(user["username"], str)
    assert len(user["username"]) >= 8  # デフォルト長
    assert "@" in user["email"]
    assert "." in user["email"].split("@")[1]


def test_user_factory_with_overrides():
    """ユーザーファクトリのオーバーライド機能をテスト."""
    custom_user = user_factory(
        id=999,
        username="custom_user",
        email="custom@example.com",
        is_active=False
    )
    
    assert custom_user["id"] == 999
    assert custom_user["username"] == "custom_user"
    assert custom_user["email"] == "custom@example.com"
    assert custom_user["is_active"] is False
    # 他のフィールドはデフォルト値のまま
    assert "full_name" in custom_user
    assert isinstance(custom_user["created_at"], datetime)


def test_book_factory():
    """書籍ファクトリが正しく動作することを確認するテスト."""
    book = book_factory()
    assert "id" in book
    assert "title" in book
    assert "author" in book
    assert "genre" in book
    assert "publication_year" in book
    assert "isbn" in book
    assert "page_count" in book
    assert "language" in book
    
    # 値の範囲をチェック
    assert 1950 <= book["publication_year"] <= 2023
    assert len(book["isbn"]) >= 10  # 最小のISBN長
    assert book["language"] in ["日本語", "英語", "フランス語", "ドイツ語"]


def test_relationship_factories():
    """関連するエンティティのファクトリを一緒に使用するテスト."""
    # 書籍を作成
    book = book_factory(title="テスト用書籍")
    
    # その書籍のキャラクターを作成
    character = character_factory(
        book_id=book["id"],
        name="テストキャラクター"
    )
    
    # その書籍の章を作成
    chapter = chapter_factory(
        book_id=book["id"],
        chapter_number=1
    )
    
    # 関連性を確認
    assert character["book_id"] == book["id"]
    assert chapter["book_id"] == book["id"]
    assert character["name"] == "テストキャラクター"
    assert chapter["title"] == "第1章"