from __future__ import annotations

"""
database/repo_bible.py - バイブル(Bible)データ操作用のリポジトリMixin
"""
import json
import logging
import time
from typing import Any, Optional

from sqlalchemy import select

from src.backend.database.core import retry_with_logging
from src.backend.database.models import Bible, Book, Branch, Character, Plot
from src.models import BibleDbModel, WorldBible

logger = logging.getLogger(__name__)


class BibleRepositoryMixin:
    """Bibleテーブルに関するDB操作をまとめたMixin"""

    @retry_with_logging()
    async def create_bible(self, book_id: int, settings: Any, version: int, last_updated: str) -> None:
        async with self._get_session() as session:
            bible = Bible(
                book_id=book_id,
                settings=json.dumps(settings, ensure_ascii=False) if not isinstance(settings, str) else settings,
                version=version,
                last_updated=last_updated
            )
            session.add(bible)

    @retry_with_logging()
    async def get_latest_bible(self, book_id: int) -> Optional[BibleDbModel]:
        async with self._get_session() as session:
            result = await session.execute(
                select(Bible).where(Bible.book_id == book_id).order_by(Bible.id.desc()).limit(1)
            )
            bible = result.scalar_one_or_none()
            if not bible:
                return None
            return BibleDbModel(**self._parse_row(self._to_dict(bible), ['settings']))

    @retry_with_logging()
    async def save_full_world_bible(self, bible: WorldBible, **kwargs) -> int:
        """WorldBible オブジェクトとその構成要素を一括保存する。book_id が指定されている場合は更新を行う。"""
        import traceback
        book_id = kwargs.get("book_id")
        branch_id = 1
        try:
            async with self._get_session() as session:
                style_dna = json.dumps({"mode": bible.style_key}, ensure_ascii=False)
                mkt_data = json.dumps(bible.marketing_assets.model_dump(), ensure_ascii=False)

                if book_id:
                    result = await session.execute(select(Book).where(Book.id == book_id))
                    book_obj = result.scalar_one_or_none()
                    if not book_obj:
                        raise ValueError(f"Book with ID {book_id} not found.")

                    current_mkt = {}
                    if book_obj.marketing_data:
                        try:
                            current_mkt = json.loads(book_obj.marketing_data)
                        except:
                            pass

                    new_mkt = bible.marketing_assets.model_dump()
                    merged_mkt = {
                        "catchcopies": current_mkt.get("catchcopies") if current_mkt.get("catchcopies") else new_mkt.get("catchcopies"),
                        "tags": current_mkt.get("tags") if current_mkt.get("tags") else new_mkt.get("tags"),
                        "ab_test_candidates": new_mkt.get("ab_test_candidates")
                    }
                    mkt_data = json.dumps(merged_mkt, ensure_ascii=False)

                    branch_id = book_obj.current_branch_id

                    book_obj.title = bible.title
                    book_obj.genre = bible.genre
                    book_obj.concept = bible.concept
                    book_obj.synopsis = bible.synopsis
                    book_obj.target_eps = kwargs.get("target_eps", 50)
                    book_obj.style_dna = style_dna
                    book_obj.marketing_data = mkt_data
                else:
                    book_obj = Book(
                        title=bible.title,
                        genre=bible.genre,
                        concept=bible.concept,
                        synopsis=bible.synopsis,
                        target_eps=kwargs.get("target_eps", 50),
                        style_dna=style_dna,
                        marketing_data=mkt_data,
                        created_at=time.strftime('%Y-%m-%dT%H:%M:%S')
                    )
                    session.add(book_obj)
                    await session.flush()
                    book_id = book_obj.id
                    branch_id = None

                ws_data = bible.world_settings.model_dump()
                if not branch_id:
                    branch_obj = Branch(
                        book_id=book_id,
                        name="Main",
                        created_at=time.strftime('%Y-%m-%dT%H:%M:%S')
                    )
                    session.add(branch_obj)
                    await session.flush()
                    branch_id = branch_obj.id
                    book_obj.current_branch_id = branch_id

                ws_data.update({
                    "story_direction": bible.story_direction,
                    "dynamic_pacing_graph": [p.model_dump() for p in bible.dynamic_pacing_graph],
                    "villain_parallel_timeline": bible.villain_parallel_timeline,
                    "arcs": [a.model_dump() for a in bible.arcs],
                    "full_story_roadmap": [r.model_dump() for r in bible.full_story_roadmap],
                    "dna": getattr(bible, "dna").model_dump() if hasattr(bible, "dna") and getattr(bible, "dna") else None
                })

                bible_obj = Bible(
                    book_id=book_id,
                    settings=json.dumps(ws_data, ensure_ascii=False),
                    version=1,
                    last_updated=time.strftime('%Y-%m-%dT%H:%M:%S')
                )
                session.add(bible_obj)

                # Characters
                chars = []
                chars.append(Character(
                    book_id=book_id,
                    name=bible.mc_profile.name,
                    role="主人公",
                    registry_data=json.dumps(bible.mc_profile.model_dump(), ensure_ascii=False)
                ))
                for s in bible.sub_characters:
                    chars.append(Character(
                        book_id=book_id,
                        name=s.name,
                        role=s.role,
                        registry_data=json.dumps(s.model_dump(), ensure_ascii=False)
                    ))
                session.add_all(chars)

                # Plots
                for ep in range(1, kwargs.get("target_eps", 50) + 1):
                    # Check if plot already exists
                    plot_result = await session.execute(
                        select(Plot).where(Plot.branch_id == branch_id).where(Plot.ep_num == ep)
                    )
                    p_obj = plot_result.scalar_one_or_none()
                    if not p_obj:
                        p_obj = Plot(
                            book_id=book_id,
                            branch_id=branch_id,
                            ep_num=ep,
                            title=f"第{ep}話 (TBD)",
                            summary="計画中...",
                            status="planned",
                            current_chain_phase="Hate"
                        )
                        session.add(p_obj)
                    else:
                        p_obj.book_id = book_id
                        p_obj.title = f"第{ep}話 (TBD)"
                        p_obj.summary = "計画中..."
                        p_obj.status = "planned"
                        p_obj.current_chain_phase = "Hate"

                return book_id
        except Exception as e:
            logger.error(f"Failed to save full world bible: {e}\n{traceback.format_exc()}")
            raise

