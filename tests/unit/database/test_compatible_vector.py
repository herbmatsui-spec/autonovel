import pytest
from sqlalchemy import create_engine, Column, Integer
from sqlalchemy.orm import sessionmaker, declarative_base
from src.infrastructure.database.types.vector_type import CompatibleVector
from src.infrastructure.database.types.vector_math import cosine_similarity

Base = declarative_base()


class VectorTestModel(Base):
    __tablename__ = "vector_test_table"
    id = Column(Integer, primary_key=True)
    embedding = Column(CompatibleVector(dim=4))


def test_compatible_vector_persistence_and_similarity():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    vec = [0.1, 0.5, 0.8, -0.2]
    item = VectorTestModel(id=1, embedding=vec)
    session.add(item)
    session.commit()

    loaded = session.query(VectorTestModel).filter_by(id=1).first()
    assert loaded is not None
    assert len(loaded.embedding) == 4
    assert pytest.approx(loaded.embedding[0]) == 0.1

    # コサイン類似度計算の検証
    sim = cosine_similarity(loaded.embedding, [0.1, 0.5, 0.8, -0.2])
    assert pytest.approx(sim, 0.001) == 1.0
    session.close()