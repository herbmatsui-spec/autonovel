import logging
import re
from typing import Dict, List, Optional

from src.schemas.ux_schemas import AffinityData

logger = logging.getLogger(__name__)


class AffinityTracker:
    """キャラクターの好感度・信頼度・依存度・警戒度を追跡・更新するサービスクラス（FSM対応）"""

    POSITIVE_TRIGGERS = ["ありがとう", "好き", "頼りになる", "守る", "優しい", "一緒", "信じる", "笑顔", "赤面", "温もり", "嬉しい", "大切"]
    TRUST_TRIGGERS = ["背中を預ける", "相棒", "信じてる", "頼む", "任せた", "助かった", "約束", "仲間", "信頼"]
    NEGATIVE_TRIGGERS = ["邪魔", "嫌い", "裏切り", "失望", "離れて", "嘘つき", "冷たい", "怒り", "不信", "最低"]
    WARINESS_TRIGGERS = ["怪しい", "信用できない", "秘密", "詮索", "裏がある", "距離を置く", "油断", "警戒", "他人事"]
    DEPENDENCY_TRIGGERS = ["あなたなしでは", "離れたくない", "独り占め", "ずっと一緒", "救われた", "依存", "私だけ", "渡さない", "見捨てないで"]

    def __init__(self, initial_characters: Optional[List[str]] = None) -> None:
        self.positive_triggers = list(self.POSITIVE_TRIGGERS)
        self.trust_triggers = list(self.TRUST_TRIGGERS)
        self.negative_triggers = list(self.NEGATIVE_TRIGGERS)
        self.wariness_triggers = list(self.WARINESS_TRIGGERS)
        self.dependency_triggers = list(self.DEPENDENCY_TRIGGERS)

        self._store: Dict[str, AffinityData] = {}
        if initial_characters:
            self.initialize_characters(initial_characters)
        else:
            # 後方互換性用のデフォルト初期化
            self.initialize_characters(["メインヒロイン", "ライバル令嬢"])
            # 初期ムード・値のプリセット
            if "メインヒロイン" in self._store:
                self._store["メインヒロイン"].affinity_score = 60.0
                self._store["メインヒロイン"].dependency_score = 25.0
                self._store["メインヒロイン"].trust_score = 60.0
                self._store["メインヒロイン"].wariness_score = 20.0
                self._store["メインヒロイン"].current_mood = self._calculate_mood(self._store["メインヒロイン"])
            if "ライバル令嬢" in self._store:
                self._store["ライバル令嬢"].affinity_score = 35.0
                self._store["ライバル令嬢"].dependency_score = 10.0
                self._store["ライバル令嬢"].trust_score = 40.0
                self._store["ライバル令嬢"].wariness_score = 45.0
                self._store["ライバル令嬢"].current_mood = self._calculate_mood(self._store["ライバル令嬢"])

    def initialize_characters(self, character_names: List[str]) -> None:
        """キャラクター一覧を受け取り、未登録のものを初期化する"""
        for name in character_names:
            if not name:
                continue
            if name not in self._store:
                self._store[name] = AffinityData(
                    character_name=name,
                    affinity_score=50.0,
                    trust_score=50.0,
                    dependency_score=20.0,
                    wariness_score=30.0,
                    current_mood="neutral",
                    recent_change=0.0,
                )
                self._store[name].current_mood = self._calculate_mood(self._store[name])

    def _calculate_mood(self, data: AffinityData) -> str:
        """心理パラメータから FSM 心理ステージを算出する"""
        aff = data.affinity_score
        trust = data.trust_score
        dep = data.dependency_score
        wary = data.wariness_score

        if wary >= 60.0:
            return "wary"
        if aff >= 80.0 and dep >= 60.0:
            return "deep_love"
        if aff >= 50.0 and wary >= 35.0:
            return "tsundere"
        if aff >= 60.0 and trust >= 50.0:
            return "affectionate"
        if trust >= 40.0 or aff >= 40.0:
            return "observation"
        return "neutral"

    def get_all_affinities(self) -> List[AffinityData]:
        return list(self._store.values())

    def get_affinity(self, character_name: str) -> Optional[AffinityData]:
        return self._store.get(character_name)

    def update_from_text(self, text: str, character_name: Optional[str] = None) -> List[AffinityData]:
        """生成テキストを解析し、多次元の好感度・信頼度・依存度・警戒度を更新する"""
        if not text:
            return self.get_all_affinities()

        if character_name and character_name not in self._store:
            self.initialize_characters([character_name])

        target_chars = [character_name] if character_name and character_name in self._store else list(self._store.keys())

        for cname in target_chars:
            data = self._store[cname]
            pos_count = sum(text.count(w) for w in self.positive_triggers)
            trust_count = sum(text.count(w) for w in self.trust_triggers)
            neg_count = sum(text.count(w) for w in self.negative_triggers)
            wary_count = sum(text.count(w) for w in self.wariness_triggers)
            dep_count = sum(text.count(w) for w in self.dependency_triggers)

            # 好感度変化
            aff_change = (pos_count * 2.5) - (neg_count * 3.0)
            if aff_change == 0 and len(text) > 200:
                aff_change = 1.0  # 物語進行による自然微増

            # 信頼度変化
            trust_change = (trust_count * 3.0) + (pos_count * 1.0) - (neg_count * 2.5)

            # 警戒心変化（ネガティブ・警戒ワードで上昇、ポジティブ・信頼で減少）
            wary_change = (wary_count * 3.5) + (neg_count * 2.0) - (trust_count * 2.5) - (pos_count * 1.5)

            # 依存度変化
            dep_change = (dep_count * 3.5) + (pos_count * 0.5)

            new_aff = min(100.0, max(0.0, round(data.affinity_score + aff_change, 1)))
            new_trust = min(100.0, max(0.0, round(data.trust_score + trust_change, 1)))
            new_wary = min(100.0, max(0.0, round(data.wariness_score + wary_change, 1)))
            new_dep = min(100.0, max(0.0, round(data.dependency_score + dep_change, 1)))

            updated = AffinityData(
                character_name=cname,
                affinity_score=new_aff,
                trust_score=new_trust,
                wariness_score=new_wary,
                dependency_score=new_dep,
                current_mood="neutral",
                recent_change=round(aff_change, 1),
            )
            updated.current_mood = self._calculate_mood(updated)
            self._store[cname] = updated

        return list(self._store.values())

    def set_affinity(self, data: AffinityData) -> List[AffinityData]:
        """好感度データを直接設定・更新する"""
        if data.character_name:
            if not data.current_mood or data.current_mood == "neutral":
                data.current_mood = self._calculate_mood(data)
            self._store[data.character_name] = data
        return list(self._store.values())

