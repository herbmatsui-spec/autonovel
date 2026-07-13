from dataclasses import dataclass
from typing import List, Literal


@dataclass
class EroticBeat:
    phase: Literal["build", "peak", "afterglow"]
    desire_level: int           # 0-100
    sensory_focus: List[str]    # ["touch", "scent", "breath", "gaze", "sound"]
    consent_state: str = "implicit"  # デフォルトを implicit に

    def validate(self) -> bool:
        """desire_levelが0-100の範囲かつconsent_stateが有効かを検証する"""
        valid_consent = self.consent_state in ("explicit", "implicit", "established")
        valid_level = 0 <= self.desire_level <= 100
        return valid_consent and valid_level

@dataclass
class EroticCurve:
    beats: List[EroticBeat]
    target_intensity: int        # 0-5

    def get_peak_beat(self) -> EroticBeat | None:
        """peakフェーズのbeatを返す。存在しなければNone。"""
        for beat in self.beats:
            if beat.phase == "peak":
                return beat
        return None

    @staticmethod
    def create_default(intensity: int = 2) -> "EroticCurve":
        """デフォルトの3フェーズ曲線を生成する。"""
        return EroticCurve(
            beats=[
                EroticBeat(phase="build", desire_level=30, sensory_focus=["gaze", "scent"], consent_state="implicit"),
                EroticBeat(phase="peak", desire_level=min(intensity * 20, 100), sensory_focus=["touch", "breath", "sound"], consent_state="explicit"),
                EroticBeat(phase="afterglow", desire_level=20, sensory_focus=["touch", "gaze"], consent_state="established"),
            ],
            target_intensity=intensity,
        )

