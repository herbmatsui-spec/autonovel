import pytest
from src.backend.database.models import User, Book

def test_user_has_tenant_id():
    # Check that User model has tenant_id column
    assert hasattr(User, 'tenant_id'), "User model should have tenant_id column for multi-tenancy"

def test_book_has_tenant_id():
    # Check that Book model has tenant_id column
    assert hasattr(Book, 'tenant_id'), "Book model should have tenant_id column for multi-tenancy"