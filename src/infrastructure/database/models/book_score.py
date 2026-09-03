# src/infrastructure/database/models/book_score.py
"""BookScore ORM モデル"""
from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship
from src.infrastructure.database.models.base_orm import Base
from datetime import datetime


class BookScore(Base):
    __tablename__ = "book_scores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False, index=True)
    chapter_number = Column(Integer, nullable=False)
    overall_score = Column(Float, nullable=False)
    structure_score = Column(Float, nullable=False)
    coherency_score = Column(Float, nullable=False)
    factual_grounding_score = Column(Float, nullable=False)
    visual_textual_synergy_score = Column(Float, nullable=False)
    reader_experience_score = Column(Float, nullable=False)
    evaluated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    evaluator_version = Column(String(50), default="1.0", nullable=False)

    # リレーションシップ（必要に応じて）
    # book = relationship("Book", back_populates="scores")

    def __repr__(self):
        return f"<BookScore(book_id={self.book_id}, chapter={self.chapter_number}, overall={self.overall_score})>"