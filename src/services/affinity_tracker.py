import logging
import re
from typing import Dict, List, Optional

from src.schemas.ux_schemas import AffinityData

logger = logging.getLogger(__name__)


class AffinityTracker:
    """キャラクターの好感度および依存度を追跡・更新するサービスクラス"""

    def __init__(self) -> None:
        self.positive_triggers = ["ありがとう", "好き", "頼りになる", "守る", "優しい", "一緒", "信じる", "笑顔", "赤面", "温もり"]
        self.negative_triggers = ["邪魔", "嫌い", "裏切り", "失望", "離れて", "嘘つき", "冷たい", "怒り"]
        self.dependency_triggers = ["あなたなしでは", "離れたくない", "独り占め", "ずっと一緒", "救われた", "依存"]

        self._store: Dict[str, AffinityData] = {
            "メインヒロイン": AffinityData(
                character_name="メインヒロイン",
                affinity_score=60.0,
                dependency_score=25.0,
                current_mood="warm",
                recent_change=0.0,
            ),
            "ライバル令嬢": AffinityData(
                character_name="ライバル令嬢",
                affinity_score=35.0,
                dependency_score=10.0,
                current_mood="tsun",
                recent_change=0.0,
            ),
        }

    def get_all_affinities(self) -> List[AffinityData]:
        return list(self._store.values())

    def update_from_text(self, text: str, character_name: Optional[str] = None) -> List[AffinityData]:
        """生成テキストを解析し、好感度・依存度を更新する"""
        if not text:
            return self.get_all_affinities()

        target_chars = [character_name] if character_name and character_name in self._store else list(self._store.keys())

        for cname in target_chars:
            data = self._store[cname]
            pos_count = sum(text.count(w) for w in self.positive_triggers)
            neg_count = sum(text.count(w) for w in self.negative_triggers)
            dep_count = sum(text.count(w) for w in self.dependency_triggers)

            change = (pos_count * 2.5) - (neg_count * 3.0)
            if change == 0:
                change = 1.5  # 物語進行による自然微増

            new_affinity = min(100.0, max(0.0, round(data.affinity_score + change, 1)))
            new_dependency = min(100.0, max(0.0, round(data.dependency_score + (dep_count * 3.0), 1)))

            # ムード判定
            mood = "neutral"
            if new_affinity >= 80:
                mood = "deredere (デレデレ)"
            elif new_affinity >= 60:
                mood = "affectionate (好意的)"
            elif new_affinity <= 30:
                mood = "wary (警戒)"
            elif data.current_mood == "tsun":
                mood = "tsun (ツン)"

            self._store[cname] = AffinityData(
                character_name=cname,
                affinity_score=new_affinity,
                dependency_score=new_dependency,
                current_mood=mood,
                recent_change=round(change, 1),
            )

        return list(self._store.values())
