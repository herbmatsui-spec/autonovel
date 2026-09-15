from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, Integer
from sqlalchemy.orm import sessionmaker, declarative_base
from src.infrastructure.database.types.datetime_type import CompatibleDateTime
from src.backend.database.core import configure_sqlite_engine

Base = declarative_base()


class DateTimeTestModel(Base):
    __tablename__ = "datetime_test_table"
    id = Column(Integer, primary_key=True)
    created_at = Column(CompatibleDateTime)


def test_datetime_utc_preservation():
    engine = create_engine("sqlite:///:memory:")
    configure_sqlite_engine(engine)
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