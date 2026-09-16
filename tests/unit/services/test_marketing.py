import importlib.util
import sys
# Load the services marketing module directly from file to avoid package shadowing
spec = importlib.util.spec_from_file_location("marketing", "E:\\hhh\\src\\services\\marketing.py")
marketing = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = marketing
spec.loader.exec_module(marketing)
MarketingAgent = marketing.MarketingAgent

import pytest
from unittest.mock import MagicMock

@pytest.mark.asyncio
async def test_create_export_package_fallback():
    """Test with no repo and no book_data -> uses fallback."""
    agent = MarketingAgent(repo=None)
    zip_bytes, filename = await agent.create_export_package(book_id=1)

    assert isinstance(zip_bytes, bytes)
    assert len(zip_bytes) > 0
    assert filename == "export_1.zip"

    # Basic check: ZIP contains expected files
    import zipfile
    import io
    with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as z:
        namelist = z.namelist()
        assert "01_本文.txt" in namelist
        assert "02_キャラクター・世界観設定集.txt" in namelist
        assert "03_プロット概要.txt" in namelist
        assert "04_データダンプ.json" in namelist

@pytest.mark.asyncio
async def test_create_export_package_with_repo_returns_none():
    """Test with repo that returns None -> fallback."""
    mock_repo = MagicMock()
    mock_repo.get_book.return_value = None
    mock_repo.get_all_non_anchor_chapters.return_value = []
    mock_repo.get_all_characters.return_value = []
    mock_repo.get_latest_bible.return_value = None
    mock_repo.get_all_plots.return_value = []

    agent = MarketingAgent(repo=mock_repo)
    zip_bytes, filename = await agent.create_export_package(book_id=1)

    assert isinstance(zip_bytes, bytes)
    assert len(zip_bytes) > 0
    assert filename == "export_1.zip"

@pytest.mark.asyncio
async def test_create_export_package_with_repo_data():
    """Test with repo returning book data."""
    mock_repo = MagicMock()
    # Mock book
    mock_book = MagicMock()
    mock_book.title = "Test Title"
    mock_book.genre = "Test Genre"
    mock_book.current_branch_id = 1
    mock_repo.get_book.return_value = mock_book

    # Mock chapters
    mock_chapter = MagicMock()
    mock_chapter.ep_num = 1
    mock_chapter.title = "Test Chapter"
    mock_chapter.content = "Test content"
    mock_repo.get_all_non_anchor_chapters.return_value = [mock_chapter]

    # Mock characters
    mock_char = MagicMock()
    mock_char.name = "Test Char"
    mock_char.role = "Hero"
    mock_char.personality = "Brave"
    mock_char.ability = "Sword"
    mock_repo.get_all_characters.return_value = [mock_char]

    # Mock bible
    mock_bible = MagicMock()
    mock_bible.settings = {"world": "fantasy"}
    mock_repo.get_latest_bible.return_value = mock_bible

    # Mock plots
    mock_plot = MagicMock()
    mock_plot.ep_num = 1
    mock_plot.title = "Test Plot"
    mock_plot.one_line_summary = "Test summary"
    mock_repo.get_all_plots.return_value = [mock_plot]

    agent = MarketingAgent(repo=mock_repo)
    zip_bytes, filename = await agent.create_export_package(book_id=1)

    assert isinstance(zip_bytes, bytes)
    assert len(zip_bytes) > 0
    assert filename == "export_1.zip"

    # Verify ZIP content includes our data
    import zipfile
    import io
    import json
    with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as z:
        # Check the JSON dump
        with z.open("04_データダンプ.json") as f:
            data = json.load(f)
            assert data["title"] == "Test Title"
            assert data["genre"] == "Test Genre"
            assert len(data["chapters"]) == 1
            assert data["chapters"][0]["title"] == "Test Chapter"
            assert len(data["characters"]) == 1
            assert data["characters"][0]["name"] == "Test Char"
            assert data["bible_settings"] == {"world": "fantasy"}
            assert len(data["plots"]) == 1
            assert data["plots"][0]["title"] == "Test Plot"

@pytest.mark.asyncio
async def test_create_export_package_with_book_data_override():
    """Test that book_data overrides repo data."""
    mock_repo = MagicMock()
    mock_book = MagicMock()
    mock_book.title = "Repo Title"
    mock_book.genre = "Repo Genre"
    mock_repo.get_book.return_value = mock_book
    mock_repo.get_all_non_anchor_chapters.return_value = []
    mock_repo.get_all_characters.return_value = []
    mock_repo.get_latest_bible.return_value = None
    mock_repo.get_all_plots.return_value = []

    agent = MarketingAgent(repo=mock_repo)

    book_data = {
        "title": "Book Data Title",
        "genre": "Book Data Genre",
        "chapters": [{"ep_num": 1, "title": "Book Data Chapter", "content": "Book Data Content"}],
        "characters": [{"name": "Book Data Char", "role": "Role", "personality": "Pers", "ability": "Ability"}],
        "plots": [{"ep_num": 1, "title": "Book Data Plot", "one_line_summary": "Book Data Summary"}],
        "bible_settings": {"key": "value"}
    }

    zip_bytes, filename = await agent.create_export_package(book_id=1, book_data=book_data)

    assert isinstance(zip_bytes, bytes)
    assert len(zip_bytes) > 0
    assert filename == "export_1.zip"

    # Verify ZIP content uses book_data
    import zipfile
    import io
    import json
    with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as z:
        with z.open("04_データダンプ.json") as f:
            data = json.load(f)
            assert data["title"] == "Book Data Title"
            assert data["genre"] == "Book Data Genre"
            assert len(data["chapters"]) == 1
            assert data["chapters"][0]["title"] == "Book Data Chapter"
            assert data["chapters"][0]["content"] == "Book Data Content"
            assert len(data["characters"]) == 1
            assert data["characters"][0]["name"] == "Book Data Char"
            assert data["bible_settings"] == {"key": "value"}
            assert len(data["plots"]) == 1
            assert data["plots"][0]["title"] == "Book Data Plot"
            assert data["plots"][0]["one_line_summary"] == "Book Data Summary"
