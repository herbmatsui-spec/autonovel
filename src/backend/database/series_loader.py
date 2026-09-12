from dataclasses import dataclass
from typing import Optional
from sqlalchemy.orm import Session
import json
import logging
from src.backend.database import SessionLocal
from src.backend.database.models import Book, Bible, Chapter
from src.easy_mode import EpisodeResult, SeriesResult
from src.backend.exceptions import NoChaptersFoundError

@dataclass
class SeriesDataLoaderConfig:
    book_id: int
    branch_id: int | None = None
    include_unpublished: bool = True
    fallback_to_minimal: bool = False


def _row_to_episode_result(row) -> EpisodeResult:
    """
    Convert a chapter row (SQLAlchemy model or dict) to EpisodeResult.
    Expected row attributes: ep_num, title, content, score_story, etc.
    """
    def _get_val(key, default=None):
        if hasattr(row, key):
            val = getattr(row, key, default)
            return val if val is not None else default
        if isinstance(row, dict):
            return row.get(key, default)
        return default

    # Extract basic fields
    episode_num = _get_val('ep_num')
    title = _get_val('title', '')
    content = _get_val('content', '')
    
    # Compute word count (simple split by whitespace)
    word_count = len(content.split()) if content else 0
    
    # Audit score: use score_story if available, else default 80.0
    audit_score = _get_val('score_story')
    if audit_score is None:
        audit_score = 80.0
    else:
        audit_score = float(audit_score)
    
    # Token usage: not stored, empty dict
    token_usage = {}
    
    # Status: assume completed if content exists
    status = "completed" if content and len(content.strip()) > 0 else "pending"
    
    # Build metadata from other fields
    metadata = {
        "killer_phrase": _get_val('killer_phrase'),
        "summary": _get_val('summary'),
        "world_state": _get_val('world_state'),
        "trinity_review_log": _get_val('trinity_review_log'),
        "ai_insight": _get_val('ai_insight'),
        "tension_delta": _get_val('tension_delta'),
        "qol_delta": _get_val('qol_delta'),
        "is_anchor": _get_val('is_anchor'),
        "created_at": _get_val('created_at'),
    }
    # Remove None values from metadata
    metadata = {k: v for k, v in metadata.items() if v is not None}
    
    # For easy_mode EpisodeResult, we also need audit_passed, rewrite_count, spice_elements, needs_human_review
    # We'll set defaults: audit_passed = True if audit_score >= 60, rewrite_count = 0, spice_elements = [], needs_human_review = False
    audit_passed = audit_score >= 60.0
    rewrite_count = 0
    spice_elements = []
    needs_human_review = False
    
    return EpisodeResult(
        episode_num=episode_num,
        title=title,
        content=content,
        word_count=word_count,
        audit_score=audit_score,
        audit_passed=audit_passed,
        rewrite_count=rewrite_count,
        spice_elements=spice_elements,
        metadata=metadata,
        needs_human_review=needs_human_review,
    )


class SeriesDataLoader:
    _row_to_episode_result = staticmethod(_row_to_episode_result)

    def __init__(self, session_factory=None):
        self._session_factory = session_factory or SessionLocal

    def _load_book_metadata(self, session: Session, book_id: int) -> dict:
        """
        Load book metadata including title, genre, concept, and bible settings.
        Raises ValueError if book not found.
        """
        book = session.query(Book).filter(Book.id == book_id).first()
        if not book:
            raise ValueError(f"Book with id {book_id} not found")
        
        # Load bible settings
        bible = session.query(Bible).filter(Bible.book_id == book_id).first()
        bible_settings = {}
        if bible and bible.settings:
            try:
                bible_settings = json.loads(bible.settings)
            except json.JSONDecodeError:
                # If invalid JSON, treat as empty
                bible_settings = {}
        
        return {
            "title": book.title,
            "genre": book.genre,
            "concept": book.concept,
            "bible": bible_settings,
            # Additional fields that might be useful
            "synopsis": book.synopsis,
            "catchcopy": book.catchcopy,
            "target_eps": book.target_eps,
            "style_dna": book.style_dna,
            "status": book.status,
            "mode": book.mode,
            "marketing_data": book.marketing_data,
        }

    def _load_chapters(self, session: Session, book_id: int, branch_id: Optional[int]) -> list:
        """
        Load chapters for the given book_id, ordered by ep_num (chapter_number).
        If branch_id is provided, only load chapters for that branch.
        Returns list of Chapter ORM objects.
        """
        query = session.query(Chapter).filter(Chapter.book_id == book_id)
        if branch_id is not None:
            query = query.filter(Chapter.branch_id == branch_id)
        # Order by ep_num ascending
        query = query.order_by(Chapter.ep_num.asc())
        return query.all()

    def _normalize_episodes(self, episodes: list[EpisodeResult]) -> list[EpisodeResult]:
        """
        Normalize episode list: warn about missing numbers and empty content,
        and re-index episode numbers to be sequential starting from 1.
        """
        logger = logging.getLogger(__name__)
        
        if not episodes:
            return episodes
        
        # Check for missing numbers and empty content
        expected_num = 1
        normalized = []
        for ep in episodes:
            if ep.episode_num != expected_num:
                logger.warning(
                    f"Missing chapter number: expected {expected_num}, got {ep.episode_num}. "
                    f"Re-numbering."
                )
            # If content is empty, we still keep it but warn?
            if not ep.content or len(ep.content.strip()) == 0:
                logger.warning(f"Chapter {ep.episode_num} has empty content.")
            
            # Create a new EpisodeResult with corrected episode_num
            normalized.append(EpisodeResult(
                episode_num=expected_num,
                title=ep.title,
                content=ep.content,
                word_count=ep.word_count,
                audit_score=ep.audit_score,
                audit_passed=ep.audit_passed,
                rewrite_count=ep.rewrite_count,
                spice_elements=ep.spice_elements,
                metadata=ep.metadata,
                needs_human_review=ep.needs_human_review,
            ))
            expected_num += 1
        
        return normalized

    def load_series(self, config: SeriesDataLoaderConfig) -> SeriesResult:
        """
        Load series metadata and chapters, construct SeriesResult.
        """
        with self._session_factory() as session:
            # Load book metadata
            metadata = self._load_book_metadata(session, config.book_id)
            
            # Load chapters
            chapters = self._load_chapters(session, config.book_id, config.branch_id)
            
            # Convert chapters to EpisodeResult
            episodes = [_row_to_episode_result(ch) for ch in chapters]
            
            # Normalize episodes (handle missing numbers, empty content)
            episodes = self._normalize_episodes(episodes)
            
            # If no chapters and fallback_to_minimal is False, raise exception
            if not episodes and not config.fallback_to_minimal:
                raise NoChaptersFoundError(f"No chapters found for book {config.book_id}")
            
            # If no chapters and fallback_to_minimal, create a minimal episode
            if not episodes and config.fallback_to_minimal:
                episodes = [self._make_minimal_episode()]
            
            # Construct SeriesResult
            return SeriesResult(
                genre=metadata.get('genre', ''),
                title=metadata.get('title', ''),
                concept=metadata.get('concept', ''),
                total_episodes=len(episodes),
                episodes=episodes,
                bible=metadata.get('bible', {}),
                plot_outline=metadata.get('synopsis', ''),  # using synopsis as plot outline
                metadata=metadata,
                created_at=None,  # could be set from book's created_at
                status="completed",
            )
    
    def _make_minimal_episode(self) -> EpisodeResult:
        """
        Create a minimal episode for fallback.
        """
        return EpisodeResult(
            episode_num=1,
            title="",
            content="",
            word_count=0,
            audit_score=0.0,
            audit_passed=False,
            rewrite_count=0,
            spice_elements=[],
            metadata={},
            needs_human_review=True,
        )

    def save_series_to_db(self, session: Session, series: SeriesResult, book_id: int) -> None:
        """
        Save SeriesResult to the database.
        Updates book metadata, bible settings, and replaces chapters.
        """
        # Update book
        book = session.query(Book).filter(Book.id == book_id).with_for_update().first()
        if not book:
            raise ValueError(f"Book with id {book_id} not found")
        book.title = series.title
        book.genre = series.genre
        book.concept = series.concept
        book.synopsis = series.plot_outline  # using plot_outline as synopsis
        # Note: other fields like style_dna, etc. could be updated from series.metadata if needed
        # For simplicity, we only update the fields we have in SeriesResult.
        
        # Update or create Bible
        bible = session.query(Bible).filter(Bible.book_id == book_id).with_for_update().first()
        bible_settings = series.bible
        if bible:
            if bible_settings:
                bible.settings = json.dumps(bible_settings)
            else:
                bible.settings = ""
        else:
            if bible_settings:
                bible = Bible(book_id=book_id, settings=json.dumps(bible_settings))
                session.add(bible)
            # else, no bible to create
        
        # Handle chapters: delete existing chapters for this book
        deleted = session.query(Chapter).filter(Chapter.book_id == book_id).delete()
        # Insert new chapters
        for idx, ep in enumerate(series.episodes, start=1):
            chapter = Chapter(
                book_id=book_id,
                branch_id=1,  # default branch
                ep_num=idx,
                title=ep.title,
                content=ep.content,
                score_story=int(ep.audit_score) if ep.audit_score is not None else 0,
                killer_phrase="",
                summary="",
                world_state="",
                trinity_review_log="",
                ai_insight="",
                tension_delta=0,
                qol_delta=0,
                is_anchor=False,
            )
            session.add(chapter)
        # Note: we do not commit here; the caller should manage the transaction.


def get_series_loader() -> SeriesDataLoader:
    return SeriesDataLoader()