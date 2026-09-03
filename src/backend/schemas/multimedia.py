"""Multimedia 機能の Pydantic スキーマ定義。"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

AssetType = Literal["media_mix", "ebook", "if_routes", "asset_pack"]
EbookFormat = Literal["epub", "pdf", "mobi", "json"]
MediaMixFormat = Literal["manga", "audio_drama", "video", "light_novel", "webtoon"]


class MultimediaRequestBase(BaseModel):
    """全 Multimedia リクエストの基底クラス。"""

    book_id: int = Field(..., ge=1, description="対象 Book ID")


class MediaMixRequest(MultimediaRequestBase):
    """Media Mix 台本生成リクエスト。"""

    format: MediaMixFormat = "manga"
    episode_num: int | None = Field(default=None, ge=1)
    include_metadata: bool = True


class MediaMixResponse(BaseModel):
    asset_id: int
    files: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EbookExportRequest(MultimediaRequestBase):
    """電子書籍エクスポートリクエスト。"""

    formats: list[EbookFormat] = Field(default_factory=lambda: ["epub", "pdf"])  # type: ignore[arg-type]
    author: str = "AI Novel Engine"
    publisher: str = "覇権小説エンジン"


class EbookExportResponse(BaseModel):
    asset_id: int
    files: list[str] = Field(default_factory=list)
    formats: list[str] = Field(default_factory=list)


class IFRouteGenerateRequest(MultimediaRequestBase):
    """IF ルート生成リクエスト。"""

    persist: bool = Field(default=True, description="DB に永続化するか")


class IFRouteResponse(BaseModel):
    asset_id: int
    nodes: int
    entry_node_id: str
    graph: dict[str, Any] = Field(default_factory=dict)


class AssetPackRequest(BaseModel):
    """統合アセットパック生成リクエスト。"""

    book_id: int = Field(..., ge=1)
    include_if_routes: bool = True
    include_media_mix: bool = True
    include_ebook: bool = True
    ebook_formats: list[EbookFormat] = Field(default_factory=lambda: ["epub", "pdf"])  # type: ignore[arg-type]
    media_mix_formats: list[MediaMixFormat] = Field(default_factory=lambda: ["manga"])  # type: ignore[arg-type]


class AssetPackResponse(BaseModel):
    asset_id: int
    task_id: str
    file_count: int = 0
    file_path: str | None = None


class ArtifactMetaResponse(BaseModel):
    asset_id: int
    book_id: int
    asset_type: str
    format: str
    file_path: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None


class TaskStatusResponse(BaseModel):
    task_id: str
    asset_id: int | None = None
    status: Literal["pending", "running", "completed", "failed"] = "pending"
    error: str | None = None
    started_at: str | None = None
    finished_at: str | None = None


class AssetPackGenerateRequest(BaseModel):
    """`/multimedia/generate` 用リクエスト (README 互換エイリアス)。"""

    book_id: int = Field(..., ge=1)
    include_if_routes: bool = True
    include_media_mix: bool = True
    include_ebook: bool = True
    ebook_formats: list[EbookFormat] = Field(default_factory=lambda: ["epub", "pdf"])  # type: ignore[arg-type]
    media_mix_formats: list[MediaMixFormat] = Field(default_factory=lambda: ["manga"])  # type: ignore[arg-type]


class AssetPackGenerateResponse(BaseModel):
    """`/multimedia/generate` 用レスポンス (README 互換エイリアス)。"""

    asset_id: int
    task_id: str
    file_count: int = 0
    file_path: str | None = None


class AssetsByBookResponse(BaseModel):
    """`/multimedia/assets/{book_id}` 用レスポンス (README 互換エイリアス)。"""

    book_id: int
    assets: list[ArtifactMetaResponse] = Field(default_factory=list)
