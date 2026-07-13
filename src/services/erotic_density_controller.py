"""
src/services/erotic_density_controller.py
螳倩・蟇・ｺｦ繧ｳ繝ｳ繝医Ο繝ｼ繝ｩ 窶・Book蜈ｨ菴薙・繝舌Λ繝ｳ繧ｹ繧堤ｮ｡逅・☆繧九・"""
import logging
from typing import List

from config.erotic_thresholds import MAX_CONSECUTIVE_PEAK_EPISODES

logger = logging.getLogger(__name__)

class EroticDensityController:
    """Book蜈ｨ菴薙・螳倩・繧ｷ繝ｼ繝ｳ蟇・ｺｦ縺ｨ髢馴囈繧堤ｮ｡逅・☆繧九・"""

    def should_allow_peak(self, recent_intensities: List[int]) -> bool:
        """逶ｴ霑代お繝斐た繝ｼ繝峨・蠑ｷ蠎ｦ繝ｪ繧ｹ繝医°繧峨√ヴ繝ｼ繧ｯ繧ｷ繝ｼ繝ｳ繧定ｨｱ蜿ｯ縺吶ｋ縺九ｒ蛻､螳壹☆繧九・"""
        if len(recent_intensities) < MAX_CONSECUTIVE_PEAK_EPISODES:
            return True
        recent = recent_intensities[-MAX_CONSECUTIVE_PEAK_EPISODES:]
        return not all(i >= 4 for i in recent)

    def recommend_intensity(self, current_ep: int, total_eps: int, base_intensity: int) -> int:
        """該当話数の進行度に応じた推奨強度を返す。"""
        progress = current_ep / max(total_eps, 1)
        if progress < 0.2:
            return max(1, min(base_intensity, 2))
        elif progress > 0.8:
            return max(1, min(base_intensity + 1, 5))
        return max(1, base_intensity)

    def suggest_next_intensity(self, recent_intensities: List[int], base_intensity: int) -> int:
        """
        逶ｴ霑題ｩｱ謨ｰ縺ｮ蠑ｷ蠎ｦ繝ｪ繧ｹ繝医°繧峨∵ｬ｡隧ｱ縺ｮ謗ｨ螂ｨ蠑ｷ蠎ｦ繧呈署譯医☆繧九・
        騾｣邯壹ヴ繝ｼ繧ｯ縺檎ｶ壹＞縺ｦ縺・ｋ蝣ｴ蜷医・1谿ｵ髫惹ｸ九￡繧九・
        """
        if len(recent_intensities) >= MAX_CONSECUTIVE_PEAK_EPISODES:
            recent = recent_intensities[-MAX_CONSECUTIVE_PEAK_EPISODES:]
            if all(i >= 4 for i in recent):
                return max(1, base_intensity - 1)

        if len(recent_intensities) >= 1:
            last = recent_intensities[-1]
            if last >= 4:
                return max(1, base_intensity - 1)

        return base_intensity

    def compute_avg_intensity(self, intensities: List[int]) -> float:
        """Book蜈ｨ菴薙・蟷ｳ蝮・ｼｷ蠎ｦ繧堤ｮ怜・縺吶ｋ縲・"""
        if not intensities:
            return 0.0
        avg = sum(intensities) / len(intensities)
        if avg > 4.0:
            logger.warning(f"Book蜈ｨ菴薙・蟷ｳ蝮・ｼｷ蠎ｦ縺鶏avg:{avg:.1f}縺ｨ鬮倥☆縺弱∪縺吶りｪｭ閠・夢蜉ｴ縺ｮ蜿ｯ閭ｽ諤ｧ縺後≠繧翫∪縺吶＄")
        return avg
