from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, Integer
from sqlalchemy.orm import sessionmaker, declarative_base
from src.infrastructure.database.types.datetime_type import CompatibleDateTime
from src.backend.database.core import DatabaseManager

Base = declarative_base()


class DateTimeTestModel(Base):
    __tablename__ = "datetime_test_table"
    id = Column(Integer, primary_key=True)
    created_at = Column(CompatibleDateTime)


def test_datetime_utc_preservation():
    # Create a database manager to get properly configured engine
    db_manager = DatabaseManager("sqlite:///:memory:")
    # Get the sync engine for SQLite operations (needed for SQLAlchemy sync session)
    async_url = str(db_manager.engine.url)
    if async_url.startswith("sqlite+aiosqlite:"):
        sync_url = async_url.replace("sqlite+aiosqlite:", "sqlite:")
    elif async_url.startswith("postgresql+asyncpg:"):
        sync_url = async_url.replace("postgresql+asyncpg:", "postgresql:")
    else:
        sync_url = async_url
    
    engine = create_engine(sync_url)
    
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    now_utc = datetime(2026, 9, 14, 12, 0, 0, tzinfo=timezone.utc)
    item = DateTimeTestModel(id=1, created_at=now_utc)
    session.add(item)
    session.commit()

    loaded = session.query(DateTimeTestModel).filter_by(id=1).first()
    assert loaded is not None
    assert loaded.created_at.tzinfo == timezone.utc
    assert loaded.created_at.year == 2026
    session.close()
