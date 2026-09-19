"""
src/services/publishers/kakuyomu.py - カクヨム Publisher (v5.0 Step 16/17)

カクヨムの架空の外部APIエンドポイントは実在しないため、
HTTPリクエスト処理を完全撤廃し、ワンクリック整形コピー +
「エピソード新規作成画面URL」生成による安全な手動投稿支援へ一本化する。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional

from src.services.publishers.base import (
    PublisherAdapter,
    PublisherCredentials,
    PublishResult,
    AuthError,
    ValidationError,
)

logger = logging.getLogger(__name__)

# カクヨム公式Web画面（エピソード新規作成）のURLテンプレート
KAKUYOMU_WORK_URL_TEMPLATE = "https://kakuyomu.jp/works/{work_id}"
KAKUYOMU_EPISODE_NEW_URL_TEMPLATE = "https://kakuyomu.jp/works/{work_id}/episodes/new"


@dataclass
class KakuyomuCredentials(PublisherCredentials):
    """カクヨム認証情報（手動投稿支援のため実APIトークンは不要）"""

    api_token: str = ""  # 互換用（未使用）
    user_id: str = ""  # 互換用（未使用）

    def __post_init__(self):
        self.platform = "kakuyomu"


@dataclass
class KakuyomuEpisodeHandoff:
    """カクヨム投稿ハンドオフペイロード（整形済み本文 + 投稿画面URL）。"""

    work_id: str
    episode_creation_url: str  # エピソード新規作成画面URL（別タブで開く）
    title: str
    body: str  # 整形済み本文（クリップボードコピー用）
    total_characters: int = 0


class KakuyomuPublisher(PublisherAdapter):
    """カクヨム 投稿アダプタ（APIリクエストなし・URL生成 + クリップボード補助）"""

    platform = "kakuyomu"
    description = "カクヨム（ワンクリック整形コピー + 投稿画面URL生成）"

    # 手動投稿支援のためレート制限は実質無制限
    rate_limit_per_minute: int = 60
    rate_limit_per_hour: int = 3600

    def __init__(self, timeout: float = 30.0):
        super().__init__()
        self.timeout = timeout

    async def authenticate(self, credentials: KakuyomuCredentials) -> bool:
        """認証確認（実APIが存在しないためトークン検証のみ）。

        Step 16: 架空の外部APIエンドポイントへのHTTPリクエストは完全撤廃済み。
        """
        if not credentials.api_token:
            # 手動投稿支援モードではトークン不要（常にTrue）
            logger.info("カクヨム: トークンなしで認証スキップ（手動投稿支援モード）")
            return True
        return True

    async def publish(
        self, novel: dict[str, Any], chapter: dict[str, Any], credentials: KakuyomuCredentials
    ) -> PublishResult:
        """新規作品投稿（第1話）— 投稿画面URL生成のみでHTTPリクエストなし。

        Step 17: work_id を指定して「エピソード新規作成URL」を生成し、
        整形済み本文とともに返却する安全な仕様。
        """
        work_id = str(novel.get("work_id", "")).strip()
        if not work_id:
            raise ValidationError(
                "カクヨムの作品ID（work_id）が必要です。投稿画面URLを生成できません。",
                self.platform,
            )

        title = str(novel.get("title", "無題"))[:100]
        body = self._format_for_kakuyomu(chapter.get("content", ""))
        episode_url = self.get_episode_creation_url(work_id)

        return PublishResult(
            success=True,
            platform=self.platform,
            post_id=work_id,
            url=episode_url,
            metadata={
                "work_id": work_id,
                "episode_creation_url": episode_url,
                "title": title,
                "body": body,
                "total_characters": len(body),
                "message": "整形済み本文をコピーし、カクヨム投稿画面に貼り付けてください。",
            },
        )

    async def update_chapter(
        self, post_id: str, chapter: dict[str, Any], credentials: KakuyomuCredentials
    ) -> PublishResult:
        """既存作品への話追加 — 投稿画面URL生成のみでHTTPリクエストなし。"""
        work_id = str(post_id).strip()
        if not work_id:
            raise ValidationError("作品ID（post_id）が必要です。", self.platform)

        episode_num = chapter.get("ep_num", 1)
        title = str(chapter.get("title", f"第{episode_num}話"))[:100]
        body = self._format_for_kakuyomu(chapter.get("content", ""))
        episode_url = self.get_episode_creation_url(work_id)

        return PublishResult(
            success=True,
            platform=self.platform,
            post_id=work_id,
            url=episode_url,
            metadata={
                "work_id": work_id,
                "episode_creation_url": episode_url,
                "episode_number": episode_num,
                "title": title,
                "body": body,
                "total_characters": len(body),
                "message": "整形済み本文をコピーし、カクヨム投稿画面に貼り付けてください。",
            },
        )

    async def get_post_status(
        self, post_id: str, credentials: KakuyomuCredentials
    ) -> dict[str, Any]:
        """作品ステータス取得 — 作品ページURLのみを返却（HTTPリクエストなし）。"""
        work_id = str(post_id).strip()
        return {
            "work_id": work_id,
            "status": "manual_publish",
            "url": KAKUYOMU_WORK_URL_TEMPLATE.format(work_id=work_id),
            "episode_creation_url": self.get_episode_creation_url(work_id),
            "message": "カクヨムは手動投稿支援のみ対応しています。投稿画面から貼り付けてください。",
        }

    def get_episode_creation_url(self, work_id: str) -> str:
        """カクヨム「エピソード新規作成画面」URLを生成する（Step 17）。

        Args:
            work_id: カクヨム作品ID

        Returns:
            str: https://kakuyomu.jp/works/{work_id}/episodes/new
        """
        return KAKUYOMU_EPISODE_NEW_URL_TEMPLATE.format(work_id=str(work_id).strip())

    def build_episode_handoff(
        self, work_id: str, title: str, body: str
    ) -> KakuyomuEpisodeHandoff:
        """整形済み本文と投稿画面URLをまとめたハンドオフペイロードを構築する。"""
        formatted = self._format_for_kakuyomu(body)
        return KakuyomuEpisodeHandoff(
            work_id=str(work_id).strip(),
            episode_creation_url=self.get_episode_creation_url(work_id),
            title=title.strip()[:100],
            body=formatted,
            total_characters=len(formatted),
        )

    def _format_for_kakuyomu(self, content: str) -> str:
        """カクヨム用フォーマット変換（改行正規化）。"""
        content = content.replace("\r\n", "\n").replace("\r", "\n")
        return content.strip()


def create_kakuyomu_publisher(timeout: float = 30.0) -> KakuyomuPublisher:
    """ファクトリ関数"""
    return KakuyomuPublisher(timeout=timeout)
