"""Admin API router for Anti-AI detection and correction."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.services.anti_ai import (
    RuleBasedAntiAIDetector,
    AntiAICorrector,
    AntiAILoopController,
)
from src.services.anti_ai.models import AICategory

router = APIRouter(prefix="/admin/anti_ai", tags=["admin", "anti_ai"])


class DetectRequest(BaseModel):
    text: str


class DetectResponse(BaseModel):
    total_score: float
    category_scores: dict[str, float]
    total_violations: int
    violations: list[dict]


class CorrectRequest(BaseModel):
    text: str
    max_loops: int = 3
    score_threshold: float = 90.0


class CorrectResponse(BaseModel):
    original_text: str
    corrected_text: str
    final_score: float
    iterations: int
    converged: bool
    history: list[dict]


class ConfigResponse(BaseModel):
    enabled: bool
    categories: list[str]


_detector = RuleBasedAntiAIDetector()
_corrector = AntiAICorrector()
_loop_controller = AntiAILoopController()


@router.post("/detect", response_model=DetectResponse)
async def detect(request: DetectRequest):
    """Detect AI fingerprints in text."""
    if not request.text or not request.text.strip():
        raise HTTPException(status_code=400, detail="text is required")

    result = _detector.detect(request.text)
    return DetectResponse(
        total_score=result.total_score,
        category_scores={k.value: v for k, v in result.category_scores.items()},
        total_violations=len(result.violations),
        violations=[v.to_dict() for v in result.violations],
    )


@router.post("/correct", response_model=CorrectResponse)
async def correct(request: CorrectRequest):
    """Detect and correct AI fingerprints in text."""
    if not request.text or not request.text.strip():
        raise HTTPException(status_code=400, detail="text is required")

    result = _detector.detect(request.text)
    if not result.violations:
        return CorrectResponse(
            original_text=request.text,
            corrected_text=request.text,
            final_score=result.total_score,
            iterations=0,
            converged=True,
            history=[],
        )

    loop_result = _loop_controller.run_sync(
        request.text,
        max_loops=request.max_loops,
        score_threshold=request.score_threshold,
    )

    return CorrectResponse(
        original_text=request.text,
        corrected_text=loop_result.text,
        final_score=loop_result.final_score,
        iterations=loop_result.iterations,
        converged=loop_result.converged,
        history=[h.to_dict() for h in loop_result.history],
    )


@router.get("/config", response_model=ConfigResponse)
async def get_config():
    """Get Anti-AI detection configuration."""
    return ConfigResponse(
        enabled=True,
        categories=[cat.value for cat in AICategory],
    )
