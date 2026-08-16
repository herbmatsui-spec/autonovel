"""
プロット生成モジュール
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from config.constants import EP_CLIMAX, EP_FINAL

logger = logging.getLogger(__name__)


class PlotGenerator:
    """プロット自動生成（テンプレ曲線×テンプレ展開）"""

    def __init__(self, preset: Dict[str, Any], target_episodes: int):
        self.preset = preset
        self.target_episodes = target_episodes

    def generate(self, bible: Dict[str, Any]) -> List[Dict[str, Any]]:
        """プロットアウトライン生成"""
        tension_curve = self.preset.get("tension", {})
        curve_points = tension_curve.get("curve_points", [])
        catharsis_spikes = tension_curve.get("catharsis_spikes", [0.25, 0.5, 0.75, 1.0])

        # 話数分のプロットを生成
        plots = []
        for ep_num in range(1, self.target_episodes + 1):
            progress = ep_num / self.target_episodes

            # テンション値を曲線から取得
            target_tension = self.interpolate_tension(progress, curve_points)

            # カタルシス話か判定
            is_catharsis = any(abs(progress - spike) < 0.08 for spike in catharsis_spikes)

            # テンプレート展開パターン選択
            pattern = self.select_pattern(ep_num, is_catharsis)

            plot = {
                "episode": ep_num,
                "title": f"第{ep_num}話 {pattern['title_suffix']}",
                "target_tension": target_tension,
                "is_catharsis": is_catharsis,
                "pattern": pattern["name"],
                "beats": pattern["beats"],
                "hook_point": pattern["hook"],
                "catharsis_type": pattern.get("catharsis_type"),
            }
            plots.append(plot)

        return plots

    def interpolate_tension(self, progress: float, curve_points: List[List[float]]) -> float:
        """テンション曲線から進行度に対応する値を補間"""
        if not curve_points:
            return 0.5

        for i in range(len(curve_points) - 1):
            p1, t1 = curve_points[i]
            p2, t2 = curve_points[i + 1]
            if p1 <= progress <= p2:
                ratio = (progress - p1) / (p2 - p1) if p2 != p1 else 0
                return t1 + (t2 - t1) * ratio

        return curve_points[-1][1]

    def select_pattern(self, ep_num: int, is_catharsis: bool) -> Dict[str, Any]:
        """話数・カタルシス有無に応じた展開パターン選択"""
        patterns = {
            "opening": {
                "name": "opening",
                "title_suffix": "〜始まりの刻印〜",
                "beats": ["日常の提示", "異変の兆候", "決定的な事件", "新世界への扉"],
                "hook": "冒頭3行で読者の欠落を刺激",
            },
            "catharsis": {
                "name": "catharsis",
                "title_suffix": "〜逆転の咆哮〜",
                "beats": ["絶体絶命", "覚醒のトリガー", "圧倒的無双", "ざまぁの完成"],
                "hook": "カタルシス直後の余韻で次話へ",
                "catharsis_type": "major",
            },
            "development": {
                "name": "development",
                "title_suffix": "〜試練の連鎖〜",
                "beats": ["新たな敵・課題", "仲間との出会い", "スキル・戦力の拡張", "伏線の提示"],
                "hook": "次なる脅威の予兆",
            },
            "climax": {
                "name": "climax",
                "title_suffix": "〜最終決戦の序曲〜",
                "beats": ["最大の危機", "真相の暴露", "全戦力の結集", "決戦への覚悟"],
                "hook": "最終話への最大級クリフハンガー",
            },
            "resolution": {
                "name": "resolution",
                "title_suffix": "〜新たな世界の幕開け〜",
                "beats": ["完全勝利", "因果の清算", "新秩序の構築", "平穏な日常へ"],
                "hook": "エピローグへの静かな誘い",
            },
        }

        if ep_num == 1:
            return patterns["opening"]
        elif ep_num == EP_FINAL:
            return patterns["resolution"]
        elif ep_num == EP_CLIMAX:
            return patterns["climax"]
        elif is_catharsis:
            return patterns["catharsis"]
        else:
            return patterns["development"]
