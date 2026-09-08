from __future__ import annotations

"""
database/social_repository.py - ソーシャルシミュレーション（関係性・日記・コメント・履歴）用リポジトリ
"""
import logging
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any, AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from src.agents.social.journals import CharacterJournalEntry
    from src.agents.social.models import CharacterCommentEntry, RelationshipMetrics
    from src.backend.database.core import DatabaseManager

logger = logging.getLogger(__name__)


class SocialRepository:
    """ソーシャルシミュレーション関連のDB操作を集約するリポジトリ"""

    def __init__(self, db_or_session: DatabaseManager | AsyncSession | None = None):
        if isinstance(db_or_session, AsyncSession):
            self._session: AsyncSession | None = db_or_session
            self._db: Any = None
        else:
            self._session = None
            self._db = db_or_session

    @asynccontextmanager
    async def session_scope(self) -> AsyncIterator[AsyncSession]:
        """セッションを提供するコンテキストマネージャ。既存セッションがあればそれを使い、なければ新規生成する。"""
        if self._session is not None:
            yield self._session
        elif self._db is not None:
            session: AsyncSession = self._db.get_session()
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
        else:
            raise RuntimeError("SocialRepository に DatabaseManager または AsyncSession が設定されていません。")

    async def upsert_relationship(
        self,
        book_id: int,
        char_a: str,
        char_b: str,
        metrics: RelationshipMetrics,
    ) -> None:
        """キャラクターペアの関係性メトリクスを挿入または更新する (Step 7)"""
        from sqlalchemy import select
        from src.backend.database.models import CharacterRelationship

        # 一貫性のため常に char_a <= char_b の順序に正規化
        c_a, c_b = (char_a, char_b) if char_a <= char_b else (char_b, char_a)

        async with self.session_scope() as session:
            stmt = select(CharacterRelationship).where(
                CharacterRelationship.book_id == book_id,
                CharacterRelationship.char_a == c_a,
                CharacterRelationship.char_b == c_b,
            )
            result = await session.execute(stmt)
            rel = result.scalar_one_or_none()

            affinity = getattr(metrics, "affinity_score", 50.0)
            trust = getattr(metrics, "trust_score", 50.0)
            tension = getattr(metrics, "tension_score", 50.0)
            depth = getattr(metrics, "depth", (affinity + trust) / 2.0)
            dynamics_state = getattr(metrics, "dynamics_state", "active")
            last_ep = getattr(metrics, "last_interaction_ep", 1)

            if rel is None:
                rel = CharacterRelationship(
                    book_id=book_id,
                    char_a=c_a,
                    char_b=c_b,
                    affection=affinity,
                    trust=trust,
                    tension=tension,
                    depth=depth,
                    dynamics_state=dynamics_state,
                    last_interaction_ep=last_ep,
                )
                session.add(rel)
            else:
                rel.affection = affinity
                rel.trust = trust
                rel.tension = tension
                rel.depth = depth
                rel.dynamics_state = dynamics_state
                rel.last_interaction_ep = last_ep

    async def get_relationship(
        self,
        book_id: int,
        char_a: str,
        char_b: str,
    ) -> RelationshipMetrics | None:
        """指定したキャラクターペアの関係性メトリクスを取得する (Step 8)"""
        from sqlalchemy import select
        from src.agents.social.models import RelationshipMetrics
        from src.backend.database.models import CharacterRelationship

        c_a, c_b = (char_a, char_b) if char_a <= char_b else (char_b, char_a)

        async with self.session_scope() as session:
            stmt = select(CharacterRelationship).where(
                CharacterRelationship.book_id == book_id,
                CharacterRelationship.char_a == c_a,
                CharacterRelationship.char_b == c_b,
            )
            result = await session.execute(stmt)
            rel = result.scalar_one_or_none()
            if rel is None:
                return None

            return RelationshipMetrics(
                char_a=char_a,
                char_b=char_b,
                trust_score=rel.trust,
                tension_score=rel.tension,
                affinity_score=rel.affection,
                dynamics_state=rel.dynamics_state or "neutral",
                last_interaction_ep=rel.last_interaction_ep,
            )

    async def get_all_relationships(
        self,
        book_id: int,
    ) -> dict[tuple[str, str], RelationshipMetrics]:
        """指定した作品の全キャラクター間関係性を取得する (Step 8)"""
        from sqlalchemy import select
        from src.agents.social.models import RelationshipMetrics
        from src.backend.database.models import CharacterRelationship

        async with self.session_scope() as session:
            stmt = select(CharacterRelationship).where(
                CharacterRelationship.book_id == book_id,
            )
            result = await session.execute(stmt)
            rows = result.scalars().all()

            store: dict[tuple[str, str], RelationshipMetrics] = {}
            for row in rows:
                metrics = RelationshipMetrics(
                    char_a=row.char_a,
                    char_b=row.char_b,
                    trust_score=row.trust,
                    tension_score=row.tension,
                    affinity_score=row.affection,
                    dynamics_state=row.dynamics_state or "neutral",
                    last_interaction_ep=row.last_interaction_ep,
                )
                store[(row.char_a, row.char_b)] = metrics
                store[(row.char_b, row.char_a)] = metrics
            return store

    async def record_history(
        self,
        book_id: int,
        char_a: str,
        char_b: str,
        episode_num: int,
        metrics: RelationshipMetrics,
        trigger_event: str = "",
    ) -> None:
        """関係性の時系列スナップショットを記録する (Step 9)"""
        from sqlalchemy import select
        from src.backend.database.models import CharacterRelationship, RelationshipHistory

        c_a, c_b = (char_a, char_b) if char_a <= char_b else (char_b, char_a)

        async with self.session_scope() as session:
            stmt = select(CharacterRelationship).where(
                CharacterRelationship.book_id == book_id,
                CharacterRelationship.char_a == c_a,
                CharacterRelationship.char_b == c_b,
            )
            result = await session.execute(stmt)
            rel = result.scalar_one_or_none()

            affinity = getattr(metrics, "affinity_score", 50.0)
            trust = getattr(metrics, "trust_score", 50.0)
            tension = getattr(metrics, "tension_score", 50.0)
            depth = getattr(metrics, "depth", (affinity + trust) / 2.0)
            dynamics_state = getattr(metrics, "dynamics_state", "active")

            if rel is None:
                rel = CharacterRelationship(
                    book_id=book_id,
                    char_a=c_a,
                    char_b=c_b,
                    affection=affinity,
                    trust=trust,
                    tension=tension,
                    depth=depth,
                    dynamics_state=dynamics_state,
                    last_interaction_ep=episode_num,
                )
                session.add(rel)
                await session.flush()

            history = RelationshipHistory(
                relationship_id=rel.id,
                episode_num=episode_num,
                affection=affinity,
                trust=trust,
                tension=tension,
                depth=depth,
                dynamics_state=dynamics_state,
                trigger_event=trigger_event,
            )
            session.add(history)

    # Alias for convenience
    record_relationship_history = record_history

    async def get_relationship_history(
        self,
        book_id: int,
        char_a: str,
        char_b: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """関係性の履歴をエピソード昇順で取得する (Step 10)"""
        from sqlalchemy import select
        from src.backend.database.models import CharacterRelationship, RelationshipHistory

        c_a, c_b = (char_a, char_b) if char_a <= char_b else (char_b, char_a)

        async with self.session_scope() as session:
            stmt = select(CharacterRelationship).where(
                CharacterRelationship.book_id == book_id,
                CharacterRelationship.char_a == c_a,
                CharacterRelationship.char_b == c_b,
            )
            result = await session.execute(stmt)
            rel = result.scalar_one_or_none()
            if rel is None:
                return []

            hist_stmt = (
                select(RelationshipHistory)
                .where(RelationshipHistory.relationship_id == rel.id)
                .order_by(RelationshipHistory.episode_num.desc())
                .limit(limit)
            )
            hist_result = await session.execute(hist_stmt)
            records = list(hist_result.scalars().all())
            records.reverse()  # 昇順に戻す

            return [
                {
                    "relationship_id": r.relationship_id,
                    "episode_num": r.episode_num,
                    "affection": r.affection,
                    "trust": r.trust,
                    "tension": r.tension,
                    "depth": r.depth,
                    "dynamics_state": r.dynamics_state,
                    "trigger_event": r.trigger_event,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in records
            ]

    async def save_journal(
        self,
        book_id: int,
        character_name: str,
        episode_num: int,
        journal: Any,
    ) -> None:
        """キャラクターの日記エントリを保存する (Step 11)"""
        from src.backend.database.models import CharacterJournal

        content = getattr(journal, "content", None)
        if content is None and isinstance(journal, dict):
            content = journal.get("content", "")
        content = content or ""

        emotion = getattr(journal, "emotion", None)
        if emotion is None and isinstance(journal, dict):
            emotion = journal.get("emotion", "")
        emotion = emotion or ""

        secret = getattr(journal, "secret_thought", None)
        if secret is None and isinstance(journal, dict):
            secret = journal.get("secret_thought", "")
        secret = secret or ""

        async with self.session_scope() as session:
            entry = CharacterJournal(
                book_id=book_id,
                character_name=character_name,
                episode_num=episode_num,
                entry_text=content,
                emotional_state=emotion,
                secret_thought=secret,
            )
            session.add(entry)

    async def get_journals(
        self,
        book_id: int,
        episode_num: int | None = None,
        character_name: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """条件に合致するキャラクター日記を取得する (Step 11)"""
        from sqlalchemy import select
        from src.backend.database.models import CharacterJournal

        async with self.session_scope() as session:
            stmt = select(CharacterJournal).where(CharacterJournal.book_id == book_id)
            if episode_num is not None:
                stmt = stmt.where(CharacterJournal.episode_num == episode_num)
            if character_name is not None:
                stmt = stmt.where(CharacterJournal.character_name == character_name)
            stmt = stmt.order_by(CharacterJournal.id.desc()).limit(limit)

            result = await session.execute(stmt)
            rows = result.scalars().all()
            return [
                {
                    "id": r.id,
                    "book_id": r.book_id,
                    "character_name": r.character_name,
                    "episode_num": r.episode_num,
                    "entry_text": r.entry_text,
                    "emotional_state": r.emotional_state,
                    "secret_thought": r.secret_thought,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in rows
            ]

    async def save_comment(
        self,
        book_id: int,
        character_name: str,
        episode_num: int,
        comment: Any,
    ) -> None:
        """キャラクターのコメントを保存する (Step 12)"""
        from src.backend.database.models import CharacterComment

        content = getattr(comment, "content", None)
        if content is None and isinstance(comment, dict):
            content = comment.get("content", "")
        content = content or ""

        topic = getattr(comment, "reaction_type", None) or getattr(comment, "topic", None)
        if topic is None and isinstance(comment, dict):
            topic = comment.get("reaction_type") or comment.get("topic", "")
        topic = topic or ""

        sentiment = getattr(comment, "sentiment", None) or getattr(comment, "reaction_type", None)
        if sentiment is None and isinstance(comment, dict):
            sentiment = comment.get("sentiment") or comment.get("reaction_type", "neutral")
        sentiment = sentiment or "neutral"

        async with self.session_scope() as session:
            entry = CharacterComment(
                book_id=book_id,
                character_name=character_name,
                episode_num=episode_num,
                comment_text=content,
                topic=topic,
                sentiment=sentiment,
            )
            session.add(entry)

    async def get_comments(
        self,
        book_id: int,
        episode_num: int | None = None,
        character_name: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """条件に合致するキャラクターコメントを取得する (Step 12)"""
        from sqlalchemy import select
        from src.backend.database.models import CharacterComment

        async with self.session_scope() as session:
            stmt = select(CharacterComment).where(CharacterComment.book_id == book_id)
            if episode_num is not None:
                stmt = stmt.where(CharacterComment.episode_num == episode_num)
            if character_name is not None:
                stmt = stmt.where(CharacterComment.character_name == character_name)
            stmt = stmt.order_by(CharacterComment.id.desc()).limit(limit)

            result = await session.execute(stmt)
            rows = result.scalars().all()
            return [
                {
                    "id": r.id,
                    "book_id": r.book_id,
                    "character_name": r.character_name,
                    "episode_num": r.episode_num,
                    "comment_text": r.comment_text,
                    "topic": r.topic,
                    "sentiment": r.sentiment,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in rows
            ]

    async def cleanup_old_history(
        self,
        book_id: int,
        keep_latest_per_pair: int = 100,
    ) -> int:
        """指定作品の古い関係性履歴を整理し、ペアごとに最新N件のみを残して古い履歴を削除 (Step 26)"""
        from sqlalchemy import delete, select
        from src.backend.database.models import CharacterRelationship, RelationshipHistory

        deleted_total = 0
        async with self.session_scope() as session:
            # 当該作品の関係性を取得
            rel_stmt = select(CharacterRelationship.id).where(CharacterRelationship.book_id == book_id)
            rel_res = await session.execute(rel_stmt)
            rel_ids = rel_res.scalars().all()

            for rid in rel_ids:
                # 当該関係性の最新 keep_latest_per_pair 件のIDを取得
                keep_stmt = (
                    select(RelationshipHistory.id)
                    .where(RelationshipHistory.relationship_id == rid)
                    .order_by(RelationshipHistory.episode_num.desc(), RelationshipHistory.id.desc())
                    .limit(keep_latest_per_pair)
                )
                keep_res = await session.execute(keep_stmt)
                keep_ids = set(keep_res.scalars().all())

                if not keep_ids:
                    continue

                # keep_ids に含まれない古いレコードを削除
                del_stmt = (
                    delete(RelationshipHistory)
                    .where(
                        RelationshipHistory.relationship_id == rid,
                        ~RelationshipHistory.id.in_(keep_ids),
                    )
                )
                del_res = await session.execute(del_stmt)
                deleted_total += del_res.rowcount or 0

        return deleted_total

    async def get_important_journals_summary(
        self,
        book_id: int,
        current_ep: int,
        lookback: int = 5,
        limit: int = 6,
    ) -> str:
        """直近過去Nエピソードの重要内面手記を取得し、プロンプト用サマリー文字列を生成 (Step 28)"""
        from sqlalchemy import select
        from src.backend.database.models import CharacterJournal

        start_ep = max(1, current_ep - lookback)
        end_ep = max(1, current_ep - 1)

        if current_ep <= 1:
            return ""

        async with self.session_scope() as session:
            stmt = (
                select(CharacterJournal)
                .where(
                    CharacterJournal.book_id == book_id,
                    CharacterJournal.episode_num >= start_ep,
                    CharacterJournal.episode_num <= end_ep,
                )
                .order_by(CharacterJournal.episode_num.desc(), CharacterJournal.id.desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            journals = result.scalars().all()

            if not journals:
                return ""

            lines = []
            for j in reversed(journals):  # エピソード昇順で表示
                secret = f" [秘めた本音: {j.secret_thought[:60]}]" if j.secret_thought else ""
                lines.append(
                    f"- 第{j.episode_num}話 {j.character_name}（感情: {j.emotional_state or '思索'}）: 「{j.entry_text[:120]}」{secret}"
                )

            return "【直近エピソードの登場人物内面手記・独白ログ】\n" + "\n".join(lines)

    async def get_relationship_trends_summary(
        self,
        book_id: int,
        limit_pairs: int = 8,
    ) -> str:
        """主要キャラクターペアの最新関係性と動的トレンドの要約テキストを生成 (Step 29)"""
        from sqlalchemy import select
        from src.backend.database.models import CharacterRelationship, RelationshipHistory

        async with self.session_scope() as session:
            stmt = (
                select(CharacterRelationship)
                .where(CharacterRelationship.book_id == book_id)
                .order_by(CharacterRelationship.last_interaction_ep.desc())
                .limit(limit_pairs)
            )
            result = await session.execute(stmt)
            rels = result.scalars().all()

            if not rels:
                return ""

            lines = []
            for rel in rels:
                # 過去の履歴からトレンドを計算
                hist_stmt = (
                    select(RelationshipHistory)
                    .where(RelationshipHistory.relationship_id == rel.id)
                    .order_by(RelationshipHistory.episode_num.desc())
                    .limit(3)
                )
                h_res = await session.execute(hist_stmt)
                hist_records = list(h_res.scalars().all())

                trend_desc = ""
                if len(hist_records) >= 2:
                    t_diff = hist_records[0].trust - hist_records[-1].trust
                    ten_diff = hist_records[0].tension - hist_records[-1].tension
                    if t_diff >= 10.0 and ten_diff <= -5.0:
                        trend_desc = "（信頼深化中↑）"
                    elif ten_diff >= 10.0:
                        trend_desc = "（緊張高揚中⚠）"
                    elif t_diff <= -10.0:
                        trend_desc = "（不和・距離拡大↓）"

                state_labels = {
                    "allies": "盟友",
                    "friends": "仲間",
                    "hostile": "敵対",
                    "rivals": "好敵手",
                    "strangers": "疎遠",
                    "neutral": "通常",
                }
                label = state_labels.get(rel.dynamics_state, rel.dynamics_state)

                lines.append(
                    f"- {rel.char_a} ⇔ {rel.char_b} [{label}]: "
                    f"信頼度={rel.trust:.0f}, 緊張度={rel.tension:.0f}, 好感度={rel.affection:.0f} {trend_desc}"
                )

            return "【登場人物間の動的心理関係性・トレンド (Social Dynamics)】\n" + "\n".join(lines)

    async def get_relationships_for_characters(
        self,
        book_id: int,
        char_names: list[str],
    ) -> list[dict[str, Any]]:
        """指定されたキャラクターリストに関連する関係性のみを抽出 (Step 32)"""
        from sqlalchemy import or_, select
        from src.backend.database.models import CharacterRelationship

        if not char_names:
            return []

        async with self.session_scope() as session:
            stmt = (
                select(CharacterRelationship)
                .where(
                    CharacterRelationship.book_id == book_id,
                    or_(
                        CharacterRelationship.char_a.in_(char_names),
                        CharacterRelationship.char_b.in_(char_names),
                    ),
                )
                .order_by(CharacterRelationship.last_interaction_ep.desc())
            )
            result = await session.execute(stmt)
            rows = result.scalars().all()

            return [
                {
                    "char_a": r.char_a,
                    "char_b": r.char_b,
                    "trust": r.trust,
                    "tension": r.tension,
                    "affection": r.affection,
                    "depth": r.depth,
                    "dynamics_state": r.dynamics_state,
                    "last_interaction_ep": r.last_interaction_ep,
                }
                for r in rows
            ]
