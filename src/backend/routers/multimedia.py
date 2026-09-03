"""Multimedia 機能の FastAPI ルータ。

`/multimedia/...` 配下に Asset Pack / Media Mix / IF Routes / eBook エンドポイント群を公開する。
`ENABLE_MULTIMEDIA` フラグが無効な場合は 503 を返す。
"""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi import Path as PathParam
from fastapi.responses import FileResponse

from src.backend.auth import validate_api_key_or_raise
from src.backend.feature_flags import is_multimedia_enabled
from src.backend.multimedia_service import MultimediaService
from src.backend.multimedia_storage import get_multimedia_dir
from src.backend.observability.health import metrics
from src.backend.rate_limit import generate_limiter
from src.backend.schemas.multimedia import (
    ArtifactMetaResponse,
    AssetPackGenerateRequest,
    AssetPackGenerateResponse,
    AssetPackRequest,
    AssetPackResponse,
    AssetsByBookResponse,
    EbookExportRequest,
    EbookExportResponse,
    IFRouteGenerateRequest,
    IFRouteResponse,
    MediaMixRequest,
    MediaMixResponse,
    TaskStatusResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def get_multimedia_service() -> MultimediaService:
    """`Depends` 用のサービスプロバイダ。テストでは `app.dependency_overrides` で差し替える。"""
    return MultimediaService()


def _check_enabled() -> None:
    """Multimedia フラグが有効か確認 (HTTPException に変換)。"""
    if not is_multimedia_enabled():
        raise HTTPException(
            status_code=503,
            detail={"error": "MultimediaDisabledError", "detail": "Multimedia features are disabled"},
        )


def _safe_path_under_base(name: str) -> Path:
    """`MULTIMEDIA_OUTPUT_DIR` 配下に限定した安全なパスを返す。"""
    base = get_multimedia_dir().resolve()
    candidate = (base / name).resolve()
    if base != candidate and base not in candidate.parents:
        raise HTTPException(status_code=400, detail="Invalid path")
    return candidate


@router.post(
    "/media-mix",
    response_model=MediaMixResponse,
    responses={503: {"description": "Multimedia disabled"}},
)
def generate_media_mix(
    payload: MediaMixRequest,
    request: Request,
    service: MultimediaService = Depends(get_multimedia_service),
    _api_key: str = Depends(validate_api_key_or_raise),
) -> MediaMixResponse:
    """Media Mix 台本生成。"""
    _check_enabled()
    generate_limiter.check(request)
    metrics.increment("multimedia_requests_total")
    logger.info("multimedia.media_mix book_id=%s format=%s", payload.book_id, payload.format)
    try:
        result = service.generate_media_mix(
            book_id=payload.book_id,
            format_name=payload.format,
            episode_num=payload.episode_num,
        )
    except Exception:
        metrics.increment("multimedia_errors_total")
        raise
    return MediaMixResponse(
        asset_id=result.asset_id or 0,
        files=result.files,
        metadata=result.metadata,
    )


@router.post(
    "/ebook",
    response_model=EbookExportResponse,
    responses={503: {"description": "Multimedia disabled"}},
)
def export_ebook(
    payload: EbookExportRequest,
    request: Request,
    service: MultimediaService = Depends(get_multimedia_service),
    _api_key: str = Depends(validate_api_key_or_raise),
) -> EbookExportResponse:
    """Ebook エクスポート (EPUB/PDF/MOBI)。"""
    _check_enabled()
    generate_limiter.check(request)
    logger.info("multimedia.ebook book_id=%s formats=%s", payload.book_id, payload.formats)
    result = service.export_ebook(book_id=payload.book_id, formats=payload.formats)
    return EbookExportResponse(
        asset_id=result.asset_id or 0,
        files=result.files,
        formats=list(result.metadata.get("formats", [])),
    )


@router.post(
    "/if-routes",
    response_model=IFRouteResponse,
    responses={503: {"description": "Multimedia disabled"}},
)
def generate_if_routes(
    payload: IFRouteGenerateRequest,
    request: Request,
    service: MultimediaService = Depends(get_multimedia_service),
    _api_key: str = Depends(validate_api_key_or_raise),
) -> IFRouteResponse:
    """IF ルートグラフ生成。"""
    _check_enabled()
    generate_limiter.check(request)
    logger.info("multimedia.if_routes book_id=%s persist=%s", payload.book_id, payload.persist)
    result, graph = service.generate_if_routes(
        book_id=payload.book_id, persist=payload.persist
    )
    if graph is None:
        raise HTTPException(status_code=500, detail="Failed to generate graph")
    return IFRouteResponse(
        asset_id=result.asset_id or 0,
        nodes=len(graph.nodes),
        entry_node_id=graph.entry_node_id,
        graph={"nodes": {nid: n.to_dict() for nid, n in graph.nodes.items()}},
    )


@router.post(
    "/asset-pack",
    response_model=AssetPackResponse,
    responses={503: {"description": "Multimedia disabled"}},
)
def generate_asset_pack(
    payload: AssetPackRequest,
    request: Request,
    service: MultimediaService = Depends(get_multimedia_service),
    _api_key: str = Depends(validate_api_key_or_raise),
) -> AssetPackResponse:
    """統合アセットパック (ZIP) を生成。"""
    _check_enabled()
    generate_limiter.check(request)
    logger.info("multimedia.asset_pack book_id=%s", payload.book_id)
    result, task_id = service.generate_asset_pack(
        book_id=payload.book_id,
        include_if_routes=payload.include_if_routes,
        include_media_mix=payload.include_media_mix,
        include_ebook=payload.include_ebook,
        ebook_formats=payload.ebook_formats,
        media_mix_formats=payload.media_mix_formats,
    )
    return AssetPackResponse(
        asset_id=result.asset_id or 0,
        task_id=task_id,
        file_count=len(result.files),
        file_path=result.files[0] if result.files else None,
    )


@router.post(
    "/generate",
    response_model=AssetPackGenerateResponse,
    responses={503: {"description": "Multimedia disabled"}},
)
def generate_asset_pack_alias(
    payload: AssetPackGenerateRequest,
    request: Request,
    service: MultimediaService = Depends(get_multimedia_service),
    _api_key: str = Depends(validate_api_key_or_raise),
) -> AssetPackGenerateResponse:
    """README 互換エイリアス: 統合アセットパック (ZIP) を生成 (`/asset-pack` と同等)。"""
    _check_enabled()
    generate_limiter.check(request)
    logger.info("multimedia.generate (alias) book_id=%s", payload.book_id)
    result, task_id = service.generate_asset_pack(
        book_id=payload.book_id,
        include_if_routes=payload.include_if_routes,
        include_media_mix=payload.include_media_mix,
        include_ebook=payload.include_ebook,
        ebook_formats=payload.ebook_formats,
        media_mix_formats=payload.media_mix_formats,
    )
    return AssetPackGenerateResponse(
        asset_id=result.asset_id or 0,
        task_id=task_id,
        file_count=len(result.files),
        file_path=result.files[0] if result.files else None,
    )


@router.get(
    "/assets/{book_id}",
    response_model=AssetsByBookResponse,
    responses={503: {"description": "Multimedia disabled"}},
)
def get_assets_by_book(
    book_id: int = PathParam(..., ge=1),
    service: MultimediaService = Depends(get_multimedia_service),
) -> AssetsByBookResponse:
    """README 互換エイリアス: 指定 book_id の全アセットメタデータを取得。"""
    if not is_multimedia_enabled():
        raise HTTPException(status_code=503, detail="Multimedia disabled")
    assets = service.get_artifacts_by_book(book_id)
    return AssetsByBookResponse(
        book_id=book_id,
        assets=[ArtifactMetaResponse(**a) for a in assets],
    )


@router.get(
    "/artifacts/{asset_id}",
    response_model=ArtifactMetaResponse,
    responses={404: {"description": "Not found"}},
)
def get_artifact(
    asset_id: int = PathParam(..., ge=1),
    service: MultimediaService = Depends(get_multimedia_service),
) -> ArtifactMetaResponse:
    """成果物メタデータ取得。"""
    if not is_multimedia_enabled():
        raise HTTPException(status_code=503, detail="Multimedia disabled")
    meta = service.get_artifact(asset_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="artifact not found")
    return ArtifactMetaResponse(
        asset_id=meta["asset_id"],
        book_id=meta["book_id"],
        asset_type=meta["asset_type"],
        format=meta["format"],
        file_path=meta["file_path"],
        metadata=meta["metadata"],
        created_at=meta["created_at"],
    )


@router.get(
    "/artifacts/{asset_id}/download",
    responses={404: {"description": "Not found"}},
)
def download_artifact(
    asset_id: int = PathParam(..., ge=1),
    service: MultimediaService = Depends(get_multimedia_service),
) -> FileResponse:
    """成果物ファイル本体をダウンロード。"""
    if not is_multimedia_enabled():
        raise HTTPException(status_code=503, detail="Multimedia disabled")
    meta = service.get_artifact(asset_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="artifact not found")
    path = Path(meta["file_path"])
    if not path.exists():
        raise HTTPException(status_code=404, detail="file missing on disk")
    media_type = "application/zip" if path.suffix == ".zip" else "application/json"
    return FileResponse(path, media_type=media_type, filename=path.name)


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
def get_task(
    task_id: str = PathParam(..., min_length=1),
    service: MultimediaService = Depends(get_multimedia_service),
) -> TaskStatusResponse:
    """タスクステータス取得。"""
    if not is_multimedia_enabled():
        raise HTTPException(status_code=503, detail="Multimedia disabled")
    info = service.get_task(task_id)
    if info is None:
        raise HTTPException(status_code=404, detail="task not found")
    return TaskStatusResponse(
        task_id=info["task_id"],
        asset_id=info.get("asset_id"),
        status=info.get("status", "pending"),
        error=info.get("error"),
        started_at=info.get("started_at"),
        finished_at=info.get("finished_at"),
    )


@router.get("/files/{filename:path}")
def serve_file(
    filename: str = PathParam(...),
) -> FileResponse:
    """`MULTIMEDIA_OUTPUT_DIR` 配下の静的ファイルを配信 (パストラバーサル防止済み)。"""
    if not is_multimedia_enabled():
        raise HTTPException(status_code=503, detail="Multimedia disabled")
    try:
        safe_path = _safe_path_under_base(filename)
    except HTTPException:
        raise
    if not safe_path.exists() or not safe_path.is_file():
        raise HTTPException(status_code=404, detail="file not found")
    media_type = "application/zip" if safe_path.suffix == ".zip" else "application/octet-stream"
    return FileResponse(safe_path, media_type=media_type, filename=safe_path.name)
