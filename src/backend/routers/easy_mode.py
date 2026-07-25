import logging
from fastapi import APIRouter, HTTPException, status

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

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/easy-mode", tags=["EasyModeUpgrade"])

gacha_service = GachaService()
digest_service = DigestService()
promotion_service = PromotionService()


@router.post("/gacha", response_model=GachaResponse)
async def create_gacha_plans(request: GachaRequest):
    """3案ガチャ（王道・変化球・ダーク）を生成する"""
    try:
        return await gacha_service.generate_plans(request)
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
    except Exception as e:
        logger.error(f"Gacha API Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AIの企画案生成に失敗しました。もう一度お試しください。",
        )


@router.post("/digest", response_model=DigestResponse)
async def create_digest(request: DigestRequest):
    """選択された企画のプロット・第1話・クライマックスダイジェストを生成する"""
    try:
        return await digest_service.generate_digest(request)
    except Exception as e:
        logger.error(f"Digest API Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ダイジェストの生成処理に失敗しました。",
        )


@router.post("/promote", response_model=PromotionResponse)
async def promote_to_advanced(request: PromotionRequest):
    """かんたんモードで生成した作品を上級者モードへ引き継ぐ"""
    try:
        return promotion_service.promote(request)
    except KeyError as ke:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="指定された作品データが見つかりません。",
        )
    except Exception as e:
        logger.error(f"Promotion API Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="上級者モードへの引き継ぎに失敗しました。",
        )
