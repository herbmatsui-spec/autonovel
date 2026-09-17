"""SQLAlchemy DeclarativeBase for ORM models."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""

    __table_args__ = {"extend_existing": True}


class BaseDbModel(Base):
    """Abstract base model for database entities."""

    __abstract__ = True
