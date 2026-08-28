import logging

from fastapi import APIRouter, Depends, HTTPException, status

from src.backend.auth import require_api_key
from src.models.easy_mode_schemas import (
    DigestRequest,
    DigestResponse,
    GachaRequest,
    GachaResponse,
    PromotionRequest,
    PromotionResponse,
)
from src.services.digest_service import DigestService
from src.services.gacha_service import GachaService
from src.services.promotion_service import PromotionService
from src.backend.response_helpers import api_success

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/easy-mode", tags=["EasyModeUpgrade"])

gacha_service = GachaService()
digest_service = DigestService()
promotion_service = PromotionService()


@router.post("/gacha")
async def create_gacha_plans(
    request: GachaRequest, api_key: str = Depends(require_api_key)
):
    """3案ガチャ（王道・変化球・ダーク）を生成する"""
    try:
        return api_success(await gacha_service.generate_plans(request), "ガチャ企画を生成しました")
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(ve),
        )
    except TimeoutError as te:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(te),
        )
    except (ConnectionError, TimeoutError, OSError) as e:
        logger.error(f"Gacha API Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AIの企画案生成に失敗しました。もう一度お試しください。",
        )


@router.post("/digest")
async def create_digest(
    request: DigestRequest, api_key: str = Depends(require_api_key)
):
    """選択された企画のプロット・第1話・クライマックスダイジェストを生成する"""
    try:
        return api_success(await digest_service.generate_digest(request), "ダイジェストを生成しました")
    except (ConnectionError, TimeoutError, OSError) as e:
        logger.error(f"Digest API Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ダイジェストの生成処理に失敗しました。",
        )


@router.post("/promote")
async def promote_to_advanced(
    request: PromotionRequest, api_key: str = Depends(require_api_key)
):
    """かんたんモードで生成した作品を上級者モードへ引き継ぐ"""
    try:
        return api_success(promotion_service.promote(request), "上級者モードへ引き継ぎました")
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="指定された作品データが見つかりません。",
        )
    except (ConnectionError, TimeoutError, OSError) as e:
        logger.error(f"Promotion API Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="上級者モードへの引き継ぎに失敗しました。",
        )
