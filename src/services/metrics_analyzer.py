import logging
import math
import re
from typing import List, Optional

from src.schemas.ux_schemas import HeatmapData, HeatmapPoint

logger = logging.getLogger(__name__)


class MetricsAnalyzer:
    """小説テキストやLLMメタデータから感情スコア（緊張感・官能度・ヘイト度など）の時系列データを抽出するアナライザー"""

    def __init__(self) -> None:
        # 感情キーワード定義（簡易ヒューリスティック）
        self.tension_keywords = ["緊迫", "敵", "剣", "怒号", "危険", "恐怖", "戦い", "激痛", "対峙", "瞬間", "殺気", "咆哮"]
        self.erotic_keywords = ["吐息", "熱", "肌", "濡れ", "震え", "密着", "唇", "甘い", "喘ぎ", "視線", "昂ぶり", "触れ"]
        self.hate_keywords = ["嘲笑", "見下す", "愚か", "傲慢", "足蹴", "踏みにじる", "奪う", "冷笑", "不条理", "屈辱"]

    def analyze_text(self, text: str, episode_id: Optional[str] = None, title: Optional[str] = None) -> HeatmapData:
        """テキストを分割し、各区間の感情スコアを計算してHeatmapDataを生成する。"""
        if not text or len(text.strip()) == 0:
            return self._generate_default_heatmap(episode_id, title)

        # テキストを10個の区間に均等分割
        num_segments = 10
        seg_len = max(1, len(text) // num_segments)
        points: List[HeatmapPoint] = []

        for i in range(num_segments):
            start = i * seg_len
            end = (i + 1) * seg_len if i < num_segments - 1 else len(text)
            segment = text[start:end]
            pos_pct = round((i / (num_segments - 1)) * 100, 1)

            t_score = self._calculate_keyword_density(segment, self.tension_keywords)
            e_score = self._calculate_keyword_density(segment, self.erotic_keywords)
            h_score = self._calculate_keyword_density(segment, self.hate_keywords)

            # 起承転結カーブのベースライン補正
            baseline_tension = math.sin((i / (num_segments - 1)) * math.pi * 0.8) * 0.4 + 0.2
            final_tension = min(1.0, round(t_score * 0.6 + baseline_tension * 0.4, 2))

            label = f"Beat {i+1}"
            if i == 0:
                label = "導入"
            elif i == num_segments - 2:
                label = "クライマックス"
            elif i == num_segments - 1:
                label = "結末・余韻"

            points.append(
                HeatmapPoint(
                    position_pct=pos_pct,
                    tension=final_tension,
                    erotic=min(1.0, round(e_score, 2)),
                    hate=min(1.0, round(h_score, 2)),
                    label=label,
                )
            )

        avg_tension = sum(p.tension for p in points) / len(points) if points else 0.0

        return HeatmapData(
            episode_id=episode_id or "ep_latest",
            title=title or "Current Episode",
            points=points,
            overall_pacing_score=round(avg_tension * 100, 1),
        )

    def _calculate_keyword_density(self, text: str, keywords: List[str]) -> float:
        if not text:
            return 0.0
        count = sum(text.count(kw) for kw in keywords)
        density = count / (max(len(text), 100) / 100.0)
        # 0.0 - 1.0 に正規化
        return min(1.0, density / 3.0)

    def _generate_default_heatmap(self, episode_id: Optional[str], title: Optional[str]) -> HeatmapData:
        """デフォルトまたはサンプル用のヒートマップデータを生成"""
        points = [
            HeatmapPoint(position_pct=0.0, tension=0.2, erotic=0.0, hate=0.1, label="発端"),
            HeatmapPoint(position_pct=25.0, tension=0.45, erotic=0.1, hate=0.5, label="対立の顕在化"),
            HeatmapPoint(position_pct=50.0, tension=0.7, erotic=0.3, hate=0.6, label="危機"),
            HeatmapPoint(position_pct=75.0, tension=0.95, erotic=0.6, hate=0.2, label="クライマックス・逆転"),
            HeatmapPoint(position_pct=100.0, tension=0.3, erotic=0.8, hate=0.0, label="余韻・解決"),
        ]
        return HeatmapData(
            episode_id=episode_id or "default_ep",
            title=title or "標準プロットカーブ",
            points=points,
            overall_pacing_score=88.5,
        )
