import pytest
from unittest.mock import AsyncMock, MagicMock
from src.backend.database.repositories.base import BaseRepository
from src.backend.database.models import Book

class TestBookRepository(BaseRepository):
    @property
    def model_class(self) -> type[Book]:
        return Book

@pytest.mark.asyncio
async def test_base_repository_get():
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = Book()
    mock_session.execute.return_value = mock_result
    
    repo = TestBookRepository(mock_session)
    result = await repo.get(1)
    
    assert result is not None
    mock_session.execute.assert_awaited_once()

@pytest.mark.asyncio
async def test_base_repository_get_all():
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [Book(), Book()]
    mock_session.execute.return_value = mock_result
    
    repo = TestBookRepository(mock_session)
    results = await repo.get_all()
    
    assert len(results) == 2
    mock_session.execute.assert_awaited_once()

@pytest.mark.asyncio
async def test_base_repository_add():
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    
    repo = TestBookRepository(mock_session)
    entity = Book()
    repo.add(entity)
    
    mock_session.add.assert_called_once_with(entity)

@pytest.mark.asyncio
async def test_base_repository_delete():
    mock_session = AsyncMock()
    mock_session.delete = AsyncMock()
    
    repo = TestBookRepository(mock_session)
    entity = Book()
    await repo.delete(entity)
    
    mock_session.delete.assert_awaited_once_with(entity)

@pytest.mark.asyncio
async def test_base_repository_delete_by_id():
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()
    
    repo = TestBookRepository(mock_session)
    await repo.delete_by_id(1)
    
    mock_session.execute.assert_awaited_once()