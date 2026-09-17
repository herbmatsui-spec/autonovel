import pytest
from unittest.mock import AsyncMock, MagicMock
from src.backend.database.repositories.base import BaseRepository
from src.backend.database.models import Book

class DummyBookRepository(BaseRepository):
    @property
    def model_class(self) -> type[Book]:
        return Book

@pytest.mark.asyncio
async def test_base_repository_get():
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = Book()
    mock_session.execute.return_value = mock_result

    repo = DummyBookRepository(mock_session)
    result = await repo.get(1)

    assert result is not None
    mock_session.execute.assert_awaited_once()

@pytest.mark.asyncio
async def test_base_repository_get_all():
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [Book(), Book()]
    mock_session.execute.return_value = mock_result

    repo = DummyBookRepository(mock_session)
    results = await repo.get_all()

    assert len(results) == 2
    mock_session.execute.assert_awaited_once()

@pytest.mark.asyncio
async def test_base_repository_add():
    mock_session = AsyncMock()
    mock_session.add = MagicMock()

    repo = DummyBookRepository(mock_session)
    entity = Book()
    repo.add(entity)

    mock_session.add.assert_called_once_with(entity)

@pytest.mark.asyncio
async def test_base_repository_delete():
    mock_session = AsyncMock()
    mock_session.delete = AsyncMock()

    repo = DummyBookRepository(mock_session)
    entity = Book()
    await repo.delete(entity)

    mock_session.delete.assert_awaited_once_with(entity)

@pytest.mark.asyncio
async def test_base_repository_delete_by_id():
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()

    repo = DummyBookRepository(mock_session)
    await repo.delete_by_id(1)

    mock_session.execute.assert_awaited_once()

def test_base_repository_to_dict_and_parse_row():
    mock_session = AsyncMock()
    repo = DummyBookRepository(mock_session)

    assert repo._to_dict(None) == {}

    row = {"data": "{\"key\": \"val\"}", "raw": 123}
    parsed = repo._parse_row(row, ["data", "non_existent"])
    assert parsed["data"] == {"key": "val"}
    assert parsed["raw"] == 123

    # Broken JSON handled gracefully
    broken_row = {"data": "{invalid json"}
    parsed_broken = repo._parse_row(broken_row, ["data"])
    assert parsed_broken["data"] == "{invalid json"
