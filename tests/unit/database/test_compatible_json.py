from sqlalchemy import create_engine, Column, Integer
from sqlalchemy.orm import sessionmaker, declarative_base
from src.infrastructure.database.types.json_type import CompatibleJSON

Base = declarative_base()


class JsonTestModel(Base):
    __tablename__ = "json_test_table"
    id = Column(Integer, primary_key=True)
    payload = Column(CompatibleJSON)


def test_compatible_json_serialization():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    data = {"novel": "異世界転生", "tags": ["ファンタジー", "無双"], "score": 98.5}
    item = JsonTestModel(id=1, payload=data)
    session.add(item)
    session.commit()

    loaded = session.query(JsonTestModel).filter_by(id=1).first()
    assert loaded is not None
    assert loaded.payload["novel"] == "異世界転生"
    assert loaded.payload["tags"] == ["ファンタジー", "無双"]
    assert loaded.payload["score"] == 98.5
    session.close()
