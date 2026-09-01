"""逆算プロット生成ワークフロー"""
from __future__ import annotations
import logging
import math
from typing import Any, List

from .base_workflow import BaseWorkflow
from src.shared.utils import StatusReporter
from src.models.plot import ArcBlueprint, CatharsisPattern
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class PlotEpisodeInit(BaseModel):
    """初期プロット構造（逆算ビルダー出力用）"""
    ep_num: int
    title: str
    one_line_summary: str
    tension: int
    catharsis: int
    is_catharsis: bool
    thematic_milestone: str
    burned_cost_or_loot: str
    antagonist_status: str
    resolution_style: str


CONFLICT_TO_ARC_TEMPLATE = {
    "ideal_vs_reality": {"arcs": 3, "pattern": "thesis_antithesis_synthesis"},
    "past_vs_future": {"arcs": 4, "pattern": "confrontation_resolution"},
    "individual_vs_org": {"arcs": 3, "pattern": "escalation_breakthrough"},
    "love_vs_duty": {"arcs": 4, "pattern": "dilemma_sacrifice"},
}

EMOTIONAL_GOAL_TO_CATHARSIS = {
    "triumph": {"type": "大カタルシス", "tensionPeak": 95, "pattern": "explosion"},
    "bittersweet": {"type": "中カタルシス", "tensionPeak": 80, "pattern": "wave"},
    "twist": {"type": "スパイク型", "tensionPeak": 90, "pattern": "spike"},
    "heartwarming": {"type": "小カタルシス連鎖", "tensionPeak": 70, "pattern": "gradual"},
}

HOOK_TO_EP1_TEMPLATE = {
    "isekai_awakening": {"tension": 40, "beats": ["awakening", "discovery", "first_use"]},
    "daily_break": {"tension": 60, "beats": ["peace", "incident", "decision"]},
    "mystery_hook": {"tension": 50, "beats": ["discovery", "investigation", "clue"]},
    "fated_meeting": {"tension": 55, "beats": ["encounter", "conflict", "realization"]},
}

ARC_SUMMARIES = {
    "ideal_vs_reality": ["理想を掲げ旅立つ", "現実の壁に打ち砕かれる", "理想と現実の統合"],
    "past_vs_future": ["過去の亡霊と対峙", "真実を知り苦悩する", "未来を選び取る", "新たな道へ"],
    "individual_vs_org": ["組織の歯車となる", "内部から崩壊を目論む", "組織を打ち破る"],
    "love_vs_duty": ["出会いと使命の板挟み", "愛を選ぶか義務を選ぶか", "犠牲を払う", "新たな均衡"],
}


class ReversePlotGenerationWorkflow(BaseWorkflow):
    """4ステップ回答からプロット構造を生成"""

    async def execute(self, reporter: StatusReporter, **kwargs) -> dict[str, Any]:
        answers = kwargs["answers"]
        target_episodes = kwargs["target_episodes"]
        genre = kwargs["genre"]

        reporter.report("回答を解析し、プロット構造を設計中...", "info")

        # 1. 回答からアーク構成を決定
        arcs = self._design_arcs(answers, target_episodes)
        reporter.update_progress(1, 3, "アーク構成完了", f"{len(arcs)}アークに分割")

        # 2. 各話の初期プロット設計
        episodes = self._design_episodes(answers, arcs, target_episodes, genre)
        reporter.update_progress(2, 3, "エピソード設計完了", f"{len(episodes)}話分生成")

        # 3. カタルシスパターン生成
        catharsis = self._design_catharsis(answers, target_episodes)
        reporter.update_progress(3, 3, "感情曲線設計完了")

        return {
            "arcs": [arc.model_dump() for arc in arcs],
            "episodes": [ep.model_dump() for ep in episodes],
            "catharsis_pattern": catharsis.model_dump(),
        }

    def _design_arcs(self, answers: dict, target_episodes: int) -> List[ArcBlueprint]:
        conflict = answers.get("coreConflict", "ideal_vs_reality")
        arc_template = CONFLICT_TO_ARC_TEMPLATE.get(conflict, {"arcs": 3, "pattern": "standard"})

        num_arcs = arc_template["arcs"]
        eps_per_arc = target_episodes // num_arcs

        arcs = []
        summaries = ARC_SUMMARIES.get(conflict, ["序盤", "中盤", "終盤"])
        for i in range(num_arcs):
            start = i * eps_per_arc + 1
            end = (i + 1) * eps_per_arc if i < num_arcs - 1 else target_episodes
            arcs.append(ArcBlueprint(
                arc_num=i + 1,
                start_ep=start,
                end_ep=end,
                title=f"第{i+1}部",
                summary=summaries[min(i, len(summaries) - 1)],
            ))
        return arcs

    def _design_episodes(self, answers: dict, arcs: List[ArcBlueprint], target_episodes: int, genre: str = "") -> List[PlotEpisodeInit]:
        emotional_goal = answers.get("emotionalGoal", "triumph")
        sacrifice = answers.get("sacrifice", "peace")
        hook = answers.get("openingHook", "isekai_awakening")

        catharsis_map = EMOTIONAL_GOAL_TO_CATHARSIS[emotional_goal]

        episodes = []
        for ep in range(1, target_episodes + 1):
            progress = ep / target_episodes
            tension = self._calc_tension(progress, catharsis_map["pattern"])
            is_catharsis = self._is_catharsis_ep(ep, target_episodes, catharsis_map["pattern"])

            episodes.append(PlotEpisodeInit(
                ep_num=ep,
                title=f"第{ep}話",
                one_line_summary=self._ep_summary(ep, target_episodes, answers),
                tension=int(tension),
                catharsis=int(tension * 0.8) if is_catharsis else 0,
                is_catharsis=is_catharsis,
                thematic_milestone=self._milestone(ep, target_episodes, answers),
                burned_cost_or_loot="なし" if ep < target_episodes else sacrifice,
                antagonist_status="強化" if ep < target_episodes * 0.7 else "弱体化",
                resolution_style="Cheat" if "ファンタジー" in genre else "Logic",
            ))
        return episodes

    def _calc_tension(self, progress: float, pattern: str) -> float:
        if pattern == "explosion":
            return 30 + 65 * (progress ** 2)
        elif pattern == "wave":
            return 40 + 40 * math.sin(progress * math.pi * 2.5)
        elif pattern == "spike":
            return 30 + 60 * progress + 20 * math.sin(progress * math.pi * 4)
        else:  # gradual
            return 30 + 50 * progress

    def _is_catharsis_ep(self, ep: int, total: int, pattern: str) -> bool:
        if pattern == "explosion":
            return ep == total
        elif pattern == "wave":
            return ep in [total // 3, 2 * total // 3, total]
        elif pattern == "spike":
            return ep in [total // 2, total]
        else:
            return ep == total

    def _design_catharsis(self, answers: dict, target_episodes: int) -> CatharsisPattern:
        emotional_goal = answers.get("emotionalGoal", "triumph")
        catharsis_map = EMOTIONAL_GOAL_TO_CATHARSIS[emotional_goal]

        catharsis_points = []
        if catharsis_map["pattern"] == "explosion":
            catharsis_points = [target_episodes]
        elif catharsis_map["pattern"] == "wave":
            catharsis_points = [target_episodes // 3, 2 * target_episodes // 3, target_episodes]
        elif catharsis_map["pattern"] == "spike":
            catharsis_points = [target_episodes // 2, target_episodes]
        else:
            catharsis_points = [target_episodes]

        return CatharsisPattern(
            pattern_type=catharsis_map["pattern"],
            catharsis_points=catharsis_points,
            tension_wave=[int(self._calc_tension(i/target_episodes, catharsis_map["pattern"]))
                         for i in range(1, target_episodes + 1)],
        )

    def _ep_summary(self, ep: int, total: int, answers: dict) -> str:
        phase = "導入" if ep <= total * 0.25 else "展開" if ep <= total * 0.75 else "結末"
        conflict = answers.get("coreConflict", "ideal_vs_reality")
        return f"[{phase}] {conflict}の局面で、主人公が選択を迫られる"

    def _milestone(self, ep: int, total: int, answers: dict) -> str:
        if ep == 1:
            return "冒険の始まり"
        elif ep == total // 3:
            return "最初の試練"
        elif ep == 2 * total // 3:
            return "最大の危機"
        elif ep == total:
            return "決着"
        return "物語の進行"