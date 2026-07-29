from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.models import Base


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    result: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[int] = mapped_column(Integer, nullable=False)

    def __init__(self, **kwargs):
        """Simple initializer to allow creating Task instances in tests.
        Stores provided keyword arguments as attributes.
        """
        for key, value in kwargs.items():
            setattr(self, key, value)
