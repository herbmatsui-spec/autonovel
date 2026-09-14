import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException
from src.backend.database.models import Book, User
from src.backend.security.roles import RoleChecker, UserRole
from src.backend.security.owner_guard import verify_book_ownership
from src.core.exceptions import NotFoundError

def test_role_checker_admin_allows_admin():
    checker = RoleChecker([UserRole.ADMIN])
    admin_user = User(id=1, email="admin@test.com", role="admin")
    assert checker(admin_user) == admin_user

def test_role_checker_admin_blocks_normal_user():
    checker = RoleChecker([UserRole.ADMIN])
    normal_user = User(id=2, email="user@test.com", role="user")
    with pytest.raises(HTTPException) as exc:
        checker(normal_user)
    assert exc.value.status_code == 403

@pytest.mark.asyncio
async def test_verify_book_ownership_success_owner():
    user = User(id=10, role="user")
    book = Book(id=100, user_id=10, title="Own Book")
    mock_uow = MagicMock()
    mock_uow.session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: book))
    
    res = await verify_book_ownership(100, user, mock_uow)
    assert res.id == 100

@pytest.mark.asyncio
async def test_verify_book_ownership_forbidden_other_user():
    user = User(id=10, role="user")
    other_book = Book(id=200, user_id=99, title="Other Book")
    mock_uow = MagicMock()
    mock_uow.session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: other_book))
    
    with pytest.raises(HTTPException) as exc:
        await verify_book_ownership(200, user, mock_uow)
    assert exc.value.status_code == 403

@pytest.mark.asyncio
async def test_verify_book_ownership_allowed_for_admin():
    admin = User(id=1, role="admin")
    other_book = Book(id=200, user_id=99, title="Other Book")
    mock_uow = MagicMock()
    mock_uow.session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: other_book))
    
    res = await verify_book_ownership(200, admin, mock_uow)
    assert res.id == 200
