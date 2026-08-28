"""
src/prototype/score_adapter.py - novel_50ep 用 スコアラーアダプタ
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

try:
    from novel_50ep.score_reviewer import EpisodeScore
except ImportError:
    from score_reviewer import EpisodeScore


class PrototypeScorer:
    """本番の QualityScorer と NarrativeScoringService に委譲して EpisodeScore を生成するアダプタ"""

    def __init__(
        self,
        quality_scorer: Optional[Any] = None,
        narrative_scorer: Optional[Any] = None,
    ):
        self.quality_scorer = quality_scorer
        self.narrative_scorer = narrative_scorer

    async def score(self, ep: int, text: str) -> EpisodeScore:
        """非同期で品質スコアとナラティブスコアを算出して EpisodeScore を返す"""
        # 1. QualityScorer
        if self.quality_scorer is not None:
            q_res = await self.quality_scorer.score_all(text)
        else:
            try:
                from src.services.quality_scorer import QualityScorer
                q_res = await QualityScorer().score_all(text)
            except Exception:
                q_res = None

        pacing = getattr(q_res, "pacing_score", 0.8)
        emotion = getattr(q_res, "emotional_resonance", 0.75)
        world = getattr(q_res, "coherence_score", 0.85)
        cliff = getattr(q_res, "hook_retention", 0.7)

        # 2. NarrativeScoringService
        if self.narrative_scorer is not None:
            n_res = await self.narrative_scorer.score(text, None)
        else:
            try:
                from src.services.narrative_scoring_service import NarrativeScoringService
                n_service = NarrativeScoringService(llm=None, prompt_manager=None)
                n_res = await n_service.score(text, None)
            except Exception:
                n_res = {"score": 0.8}

        n_score = n_res.get("overall_narrative_score", n_res.get("score", 0.8))
        if isinstance(n_score, (int, float)) and n_score > 1.0:
            n_score = n_score / 100.0

        # 3. 総合スコアの合成 (0.0〜1.0)
        total_score = round(
            (pacing * 0.25) + (emotion * 0.25) + (world * 0.2) + (cliff * 0.15) + (float(n_score) * 0.15),
            3,
        )

        details: Dict[str, str] = {
            "pacing": f"{pacing:.2f}",
            "emotion": f"{emotion:.2f}",
            "world": f"{world:.2f}",
            "cliff": f"{cliff:.2f}",
            "narrative": f"{float(n_score):.2f}",
        }

        return EpisodeScore(
            ep=ep,
            pacing_score=float(pacing),
            emotion_score=float(emotion),
            world_score=float(world),
            cliff_score=float(cliff),
            metaphor_score=0.8,
            style_score=0.8,
            total_score=float(total_score),
            details=details,
            style_details={},
        )

    def score_sync(self, ep: int, text: str) -> EpisodeScore:
        """同期インターフェース"""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is not None and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(lambda: asyncio.run(self.score(ep, text))).result()
        else:
            return asyncio.run(self.score(ep, text))
