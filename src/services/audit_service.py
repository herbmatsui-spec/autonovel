import logging
from typing import Any, List, Tuple

from src.agents.audit import AbilityConsistencyChecker, DeAIAuditor, FastPlotScreener

logger = logging.getLogger(__name__)

class AuditService:
    """監査サービス"""
    def __init__(self, llm: Any, prompt_manager: Any):
        self.fast_screener = FastPlotScreener(llm=llm, prompt_manager=prompt_manager)
        self.ability_checker = AbilityConsistencyChecker(llm=llm, prompt_manager=prompt_manager)
        self.deai_auditor = DeAIAuditor(llm=llm, prompt_manager=prompt_manager)

    async def screen_plot(self, blueprint: str) -> Tuple[bool, str]:
        return await self.fast_screener.screen_plot(blueprint)

    async def audit_ability(self, blueprint: str, settings_json: str, characters_json: str) -> Tuple[bool, str, str]:
        return await self.ability_checker.audit_ability_consistency(blueprint, settings_json, characters_json)

    async def audit_deai(self, content: str) -> Tuple[bool, str]:
        return await self.deai_auditor.audit(content)

    def get_erotic_advice(self, intensities: List[int], current_ep: int, total_eps: int) -> List[str]:
        """官能シーンのタイミングに関するAIアドバイスを返す。"""
        from src.services.erotic_density_controller import EroticDensityController
        controller = EroticDensityController()
        advice = []

        if not controller.should_allow_peak(intensities):
            advice.append("⚠️ 連続するピークシーンが多すぎます。読者疲労の可能性があります。次の1〜2話はクールダウンを推奨します。")

        avg = controller.compute_avg_intensity(intensities)
        if avg > 3.5:
            advice.append("⚠️ 全体の官能強度の平均が高めです。情緒的な「溜め」の回を増やすことを検討してください。")

        return advice
