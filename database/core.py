import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from config.base import DATABASE_URL

# Base class for all models
Base = declarative_base()

class DatabaseManager:
    """
    Database connection manager utilizing SQLAlchemy.
    Handles engine creation and session management.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, db_url: str = DATABASE_URL):
        if self._initialized:
            return

        self.logger = logging.getLogger(__name__)
        try:
            # Force synchronous driver for SQLite if the URL uses sqlite+aiosqlite
            sync_url = db_url.replace("sqlite+aiosqlite", "sqlite")
            self.engine = create_engine(
                sync_url,
                echo=False,
                pool_size=5,
                max_overflow=10,
                pool_timeout=30
            )
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
            self._initialized = True
            self.logger.info("DatabaseManager initialized successfully.")
        except Exception as e:
            self.logger.error(f"Failed to initialize DatabaseManager: {e}")
            raise

    @contextmanager
    def get_session(self) -> Generator:
        """Provides a transactional scope around a series of operations."""
        session = self.SessionLocal()
        try:
            yield session
        finally:
            session.close()

    def init_db(self):
        """Creates all tables defined in Base."""
        try:
            Base.metadata.create_all(bind=self.engine)
            self.logger.info("Database tables created successfully.")
        except Exception as e:
            self.logger.error(f"Error during DB initialization: {e}")
            raise

