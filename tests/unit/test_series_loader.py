import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.infrastructure.database.models.base_orm import Base
from src.backend.database.series_loader import SeriesDataLoader, SeriesDataLoaderConfig
from src.backend.database.models import Book, Bible, Chapter
from src.easy_mode import EpisodeResult, SeriesResult
import json

# Use an in-memory SQLite database for testing
TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture
def db_engine():
    engine = create_engine(TEST_DATABASE_URL, echo=False)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)

@pytest.fixture
def db_session(db_engine):
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.close()

@pytest.fixture
def loader(db_engine):
    # Create a session factory bound to our test engine
    SessionLocal = sessionmaker(bind=db_engine)
    return SeriesDataLoader(session_factory=SessionLocal)

def test_load_series_with_chapters(loader, db_session):
    # Create a test book
    book = Book(title="Test Book", genre="Fantasy", concept="A test concept")
    db_session.add(book)
    db_session.commit()
    db_session.refresh(book)
    
    # Create a Bible entry for the book
    bible = Bible(book_id=book.id, settings='{"theme": "epic"}')
    db_session.add(bible)
    
    # Create a few chapters
    for i in range(1, 4):
        chapter = Chapter(
            book_id=book.id,
            branch_id=1,
            ep_num=i,
            title=f"Chapter {i}",
            content=f"Content of chapter {i}",
            score_story=85,
        )
        db_session.add(chapter)
    db_session.commit()
    
    # Configure loader to load this book
    config = SeriesDataLoaderConfig(book_id=book.id, branch_id=1)
    
    # Load the series
    series = loader.load_series(config)
    
    # Assertions
    assert series.title == "Test Book"
    assert series.genre == "Fantasy"
    assert series.concept == "A test concept"
    assert series.total_episodes == 3
    assert len(series.episodes) == 3
    assert series.episodes[0].episode_num == 1
    assert series.episodes[0].title == "Chapter 1"
    assert series.episodes[0].content == "Content of chapter 1"
    assert series.episodes[0].word_count == 4  # Fixed: "Content of chapter 1" has 4 words
    assert series.bible == {"theme": "epic"}
    
def test_load_series_no_chapters_raises(loader, db_session):
    # Create a book with no chapters
    book = Book(title="Empty Book", genre="Sci-Fi", concept="A concept")
    db_session.add(book)
    db_session.commit()
    
    config = SeriesDataLoaderConfig(book_id=book.id, branch_id=1, fallback_to_minimal=False)
    
    with pytest.raises(Exception) as exc_info:
        loader.load_series(config)
    # Check that it's the expected exception
    from src.backend.exceptions import NoChaptersFoundError
    assert isinstance(exc_info.value, NoChaptersFoundError)

def test_load_series_fallback_to_minimal(loader, db_session):
    # Create a book with no chapters
    book = Book(title="Fallback Book", genre="Drama", concept="A concept")
    db_session.add(book)
    db_session.commit()
    
    config = SeriesDataLoaderConfig(book_id=book.id, branch_id=1, fallback_to_minimal=True)
    
    series = loader.load_series(config)
    
    assert series.total_episodes == 1
    assert len(series.episodes) == 1
    assert series.episodes[0].title == ""
    assert series.episodes[0].content == ""
    assert series.episodes[0].word_count == 0
    assert series.episodes[0].needs_human_review == True

def test_save_series_to_db(loader, db_session):
    # Create a book
    book = Book(title="Original Title", genre="Original Genre", concept="Original concept")
    db_session.add(book)
    db_session.commit()
    
    # Create a SeriesResult to save
    series = SeriesResult(
        genre="Updated Genre",
        title="Updated Title",
        concept="Updated concept",
        total_episodes=2,
        episodes=[
            EpisodeResult(
                episode_num=1,
                title="First Chapter",
                content="First content",
                word_count=2,
                audit_score=90.0,
                audit_passed=True,
                rewrite_count=0,
                spice_elements=[],
                metadata={},
                needs_human_review=False,
            ),
            EpisodeResult(
                episode_num=2,
                title="Second Chapter",
                content="Second content",
                word_count=2,
                audit_score=85.0,
                audit_passed=True,
                rewrite_count=0,
                spice_elements=[],
                metadata={},
                needs_human_review=False,
            ),
        ],
        bible={"setting": "value"},
        plot_outline="A plot outline",
        metadata={"extra": "data"},
    )
    
    # Save to db
    loader.save_series_to_db(db_session, series, book.id)
    db_session.commit()
    
    # Retrieve and verify
    saved_book = db_session.query(Book).filter(Book.id == book.id).first()
    assert saved_book.title == "Updated Title"
    assert saved_book.genre == "Updated Genre"
    assert saved_book.concept == "Updated concept"
    assert saved_book.synopsis == "A plot outline"
    
    saved_bible = db_session.query(Bible).filter(Bible.book_id == book.id).first()
    assert saved_bible is not None
    settings = json.loads(saved_bible.settings)
    assert settings == {"setting": "value"}
    
    saved_chapters = db_session.query(Chapter).filter(Chapter.book_id == book.id).order_by(Chapter.ep_num).all()
    assert len(saved_chapters) == 2
    assert saved_chapters[0].title == "First Chapter"
    assert saved_chapters[0].content == "First content"
    assert saved_chapters[0].score_story == 90
    assert saved_chapters[1].title == "Second Chapter"
    assert saved_chapters[1].content == "Second content"
    assert saved_chapters[1].score_story == 85