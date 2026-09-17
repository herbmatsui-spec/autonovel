"""章完了時の自動100字事実要約生成サービス (v5.0 Step 14).

長編執筆におけるコンテキスト肥大化を防止するため、
各エピソード本文から客観的事実のみを100字〜150字以内で抽出・永続化する。
"""
from __future__ import annotations

import inspect
import logging
from typing import Any, List, Optional
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.database.models_digest import EpisodeDigestModel

logger = logging.getLogger("digest_service")

MAX_DIGEST_LENGTH = 150
TARGET_DIGEST_LENGTH = 100


async def generate_episode_digest(
    llm: Any,
    draft_text: str,
    ep_num: int,
) -> str:
    """エピソード本文から後続話に影響する「確定した客観的事実」のみを100文字程度で要約抽出する。

    Args:
        llm: LLMクライアント（generate, ainvoke, predict, または呼び出し可能オブジェクト）
        draft_text: 対象エピソードの本文テキスト
        ep_num: 対象エピソードの話数

    Returns:
        150字以内の確定事実ダイジェスト文字列
    """
    if not draft_text or not draft_text.strip():
        return f"第{ep_num}話: 特筆すべき出来事なし。"

    cleaned_draft = draft_text.strip()[:2500]

    prompt = (
        f"あなたは小説の編集補助AIです。以下の第{ep_num}話本文から、"
        f"後続話のプロットや伏線・人間関係に影響する「起きた客観的事実（行動、獲得、変化など）」のみを、"
        f"感情や修飾語を省いて100文字以内で箇条書き要約してください。\n\n"
        f"【本文】\n{cleaned_draft}\n\n"
        f"【客観的事実ダイジェスト（100字以内）】"
    )

    digest_text = ""

    if llm is not None:
        try:
            # 1. llm.generate(prompt=..., temperature=0.1)
            if hasattr(llm, "generate"):
                res = llm.generate(prompt=prompt, temperature=0.1)
                if inspect.isawaitable(res):
                    res = await res
                if isinstance(res, str):
                    digest_text = res
                elif hasattr(res, "text"):
                    digest_text = res.text
                elif hasattr(res, "content"):
                    digest_text = str(res.content)
                elif isinstance(res, dict) and "content" in res:
                    digest_text = str(res["content"])
            # 2. llm.ainvoke(prompt)
            elif hasattr(llm, "ainvoke"):
                res = await llm.ainvoke(prompt)
                if hasattr(res, "content"):
                    digest_text = str(res.content)
                else:
                    digest_text = str(res)
            # 3. llm.predict(prompt)
            elif hasattr(llm, "predict"):
                res = llm.predict(prompt)
                if inspect.isawaitable(res):
                    res = await res
                digest_text = str(res)
            # 4. callable
            elif callable(llm):
                res = llm(prompt)
                if inspect.isawaitable(res):
                    res = await res
                digest_text = str(res)
        except Exception as e:
            logger.warning(f"LLM generation failed for episode {ep_num} digest: {e}")
            digest_text = ""

    # フォールバック抽出: LLMが使えないか失敗した場合は文末のキー事実を簡易抽出
    if not digest_text or not digest_text.strip():
        lines = [line.strip() for line in cleaned_draft.splitlines() if line.strip()]
        # 台詞以外の主要記述を抽出
        narrative_lines = [l for l in lines if not (l.startswith("「") or l.startswith("『"))]
        sample_lines = narrative_lines[-3:] if len(narrative_lines) >= 3 else lines[-3:]
        fallback_summary = "。".join([l.rstrip("。") for l in sample_lines])
        digest_text = f"第{ep_num}話要約: {fallback_summary}"

    # 長さ正規化 (最大 MAX_DIGEST_LENGTH 字)
    cleaned = digest_text.strip()
    if len(cleaned) > MAX_DIGEST_LENGTH:
        cleaned = cleaned[:MAX_DIGEST_LENGTH - 3].rstrip() + "..."

    return cleaned


class EpisodeDigestRepository:
    """エピソードダイジェストの非同期DB永続化リポジトリ。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def save_digest(
        self,
        book_id: int,
        episode_num: int,
        digest_text: str,
    ) -> EpisodeDigestModel:
        """エピソードダイジェストを新規作成または更新（Upsert）。"""
        stmt = select(EpisodeDigestModel).where(
            EpisodeDigestModel.book_id == book_id,
            EpisodeDigestModel.episode_num == episode_num,
        )
        res = await self.db.execute(stmt)
        existing = res.scalars().first()

        now = datetime.now(timezone.utc)
        if existing:
            existing.digest_text = digest_text
            existing.updated_at = now
            await self.db.flush()
            return existing
        else:
            record = EpisodeDigestModel(
                book_id=book_id,
                episode_num=episode_num,
                digest_text=digest_text,
                created_at=now,
                updated_at=now,
            )
            self.db.add(record)
            await self.db.flush()
            return record

    async def get_digests(
        self,
        book_id: int,
        limit: Optional[int] = None,
    ) -> List[EpisodeDigestModel]:
        """指定作品のダイジェストを話数昇順で取得する。"""
        stmt = (
            select(EpisodeDigestModel)
            .where(EpisodeDigestModel.book_id == book_id)
            .order_by(EpisodeDigestModel.episode_num.asc())
        )
        if limit:
            stmt = stmt.limit(limit)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def get_digest(
        self,
        book_id: int,
        episode_num: int,
    ) -> Optional[EpisodeDigestModel]:
        """特定話数のダイジェストを取得する。"""
        stmt = select(EpisodeDigestModel).where(
            EpisodeDigestModel.book_id == book_id,
            EpisodeDigestModel.episode_num == episode_num,
        )
        res = await self.db.execute(stmt)
        return res.scalars().first()


class EpisodeDigestService:
    """エピソードダイジェストの生成と永続化を一括管理するサービス。"""

    def __init__(
        self,
        repo: Optional[EpisodeDigestRepository] = None,
        llm: Any = None,
    ):
        self.repo = repo
        self.llm = llm

    async def summarize_and_save(
        self,
        book_id: int,
        episode_num: int,
        draft_text: str,
    ) -> str:
        """エピソード本文から事実ダイジェストを生成し、DBに保存する。"""
        digest_text = await generate_episode_digest(
            llm=self.llm,
            draft_text=draft_text,
            ep_num=episode_num,
        )

        if self.repo is not None:
            await self.repo.save_digest(
                book_id=book_id,
                episode_num=episode_num,
                digest_text=digest_text,
            )

        return digest_text
