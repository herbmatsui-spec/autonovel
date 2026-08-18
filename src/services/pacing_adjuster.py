import logging
from typing import Dict, Optional

from src.schemas.ux_schemas import ReadingSpeedData

logger = logging.getLogger(__name__)


class PacingAdjuster:
    """読者の読書速度やスクロール傾向から最適な描写密度・展開テンポを計算するサービスクラス"""

    def __init__(self) -> None:
        self._session_pacing: Dict[str, int] = {}  # session_id -> metaphor_density (10-90)

    def calculate_density(self, data: ReadingSpeedData) -> int:
        """
        スクロール速度（px/sec）や滞在時間から描写密度（10〜90）を算出する。
        - 高速読書（速読派）: 描写密度を下げ（20〜35）、テンポ・展開重視
        - 低速読書（じっくり派）: 描写密度を上げ（65〜85）、心理描写・五感比喩重視
        """
        speed = data.scroll_speed_px_per_sec
        density = 50

        if speed > 400:
            density = 20
        elif speed > 250:
            density = 35
        elif speed < 60:
            density = 80
        elif speed < 120:
            density = 65

        session_key = data.session_id or "default_session"
        self._session_pacing[session_key] = density
        logger.info(f"Pacing adjusted for session {session_key}: speed={speed:.1f}px/s -> density={density}")
        return density

    def get_current_density(self, session_id: Optional[str] = None) -> int:
        return self._session_pacing.get(session_id or "default_session", 50)
