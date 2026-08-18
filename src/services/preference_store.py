import logging
from typing import Dict, Optional

from src.schemas.ux_schemas import GapMoePreference

logger = logging.getLogger(__name__)


class PreferenceStore:
    """ユーザーごとのギャップ萌え設定や作品カスタマイズ嗜好を保持・管理するサービスクラス"""

    def __init__(self) -> None:
        self._preferences: Dict[str, GapMoePreference] = {
            "default": GapMoePreference(gap_type="tsundere", intensity=60)
        }

    def save_preference(self, user_id: str, pref: GapMoePreference) -> GapMoePreference:
        self._preferences[user_id] = pref
        logger.info(f"Saved GapMoe preference for {user_id}: {pref.gap_type} (intensity={pref.intensity})")
        return pref

    def get_preference(self, user_id: Optional[str] = None) -> GapMoePreference:
        return self._preferences.get(user_id or "default", self._preferences["default"])

    def build_custom_gap_prompt(self, user_id: Optional[str] = None) -> str:
        pref = self.get_preference(user_id)
        gap_descriptions = {
            "tsundere": "普段は強気・ツンツンしているが、二人きりになると顔を真っ赤にして照れ隠しをするギャップ",
            "kuudere_passionate": "感情を表に出さない無口・冷静キャラだが、心の中では主人公への独占欲が激しく燃え滾っているギャップ",
            "clumsy_genius": "戦闘や頭脳は圧倒的天才だが、日常的なこと（料理や片付け）ではドジを踏んで甘えてくるギャップ",
            "villainess_innocent": "悪役令嬢として高笑いしながらも、内面では小動物のようにビクビクして主人公にすがるギャップ",
        }
        desc = gap_descriptions.get(pref.gap_type, "意外な一面を見せる多層的な魅力")
        return f"【ユーザー指定ギャップ萌え補正（強度 {pref.intensity}%）】: {desc}"
