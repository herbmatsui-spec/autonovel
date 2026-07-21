"""
config/erotic_parameters.py
官能エージェント用の調整可能なパラメータ定義モジュール。
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional


DEFAULT_SENSORY_WEIGHTS = {
    "touch": 80,
    "scent": 60,
    "sound": 70,
    "gaze": 50,
    "breath": 75,
    "taste": 30,
}

DEFAULT_PACE_RATIOS = {
    "build": 3,
    "peak": 2,
    "afterglow": 2,
}


@dataclass
class EroticParameters:
    """官能エージェントの詳細パラメータ。

    ユーザーが必要なときに調整できる細やかなパラメータ群。
    """

    enabled: bool = False
    base_intensity: int = 2

    sensory_weights: Dict[str, int] = field(
        default_factory=lambda: DEFAULT_SENSORY_WEIGHTS.copy()
    )

    pace_ratios: Dict[str, int] = field(
        default_factory=lambda: DEFAULT_PACE_RATIOS.copy()
    )

    metaphor_density: int = 50
    psychology_depth: int = 50

    use_video_patterns: bool = True
    video_pattern_preference: List[str] = field(default_factory=list)

    def __post_init__(self):
        """パラメータの-validation"""
        if not 0 <= self.base_intensity <= 5:
            raise ValueError("base_intensity must be between 0 and 5")

        for sense, weight in self.sensory_weights.items():
            if not 0 <= weight <= 100:
                raise ValueError(f"sensory_weights[{sense}] must be between 0 and 100")

        for phase, ratio in self.pace_ratios.items():
            if not 1 <= ratio <= 10:
                raise ValueError(f"pace_ratios[{phase}] must be between 1 and 10")

        if not 0 <= self.metaphor_density <= 100:
            raise ValueError("metaphor_density must be between 0 and 100")

        if not 0 <= self.psychology_depth <= 100:
            raise ValueError("psychology_depth must be between 0 and 100")

    def get_sorted_sensory_priority(self) -> List[str]:
        """感覚を重み順にソートして返す。"""
        return sorted(
            self.sensory_weights.keys(),
            key=lambda k: self.sensory_weights[k],
            reverse=True,
        )

    def get_sensory_focus_for_phase(
        self, phase: str, base_senses: List[str]
    ) -> List[str]:
        """指定されたフェーズと基本感覚リストから、重み付けされた感覚リストを返す。

        Args:
            phase: フェーズ ("build", "peak", "afterglow")
            base_senses:  기본感覚リスト

        Returns:
            重み順でソートされた感覚リスト
        """
        weighted = []
        for sense in base_senses:
            weight = self.sensory_weights.get(sense, 50)
            weighted.append((sense, weight))

        weighted.sort(key=lambda x: x[1], reverse=True)
        return [s[0] for s in weighted]

    def get_beat_count_for_phase(self, phase: str) -> int:
        """指定されたフェーズのビート数をpace_ratioから算出する。

        Args:
            phase: フェーズ名

        Returns:
            ビート数（1-5の範囲）
        """
        ratio = self.pace_ratios.get(phase, 2)
        if self.base_intensity >= 4:
            return min(ratio, 5)
        elif self.base_intensity >= 3:
            return min(ratio, 3)
        else:
            return 1

    def get_metaphor_sample_size(self) -> int:
        """現在のmetaphor_densityに応じたサンプルサイズを返す。"""
        base = 5
        density_factor = int(self.metaphor_density * 0.3)
        intensity_factor = self.base_intensity * 2
        return min(base + density_factor + intensity_factor, 25)

    def get_psychology_sample_size(self) -> int:
        """現在のpsychology_depthに応じたサンプルサイズを返す。"""
        base = 4
        depth_factor = int(self.psychology_depth * 0.25)
        intensity_factor = self.base_intensity * 2
        return min(base + depth_factor + intensity_factor, 20)

    @classmethod
    def from_dict(cls, data: Dict) -> "EroticParameters":
        """辞書からパラメータを生成する。"""
        return cls(
            enabled=data.get("enabled", False),
            base_intensity=data.get("base_intensity", 2),
            sensory_weights=data.get(
                "sensory_weights", DEFAULT_SENSORY_WEIGHTS.copy()
            ),
            pace_ratios=data.get("pace_ratios", DEFAULT_PACE_RATIOS.copy()),
            metaphor_density=data.get("metaphor_density", 50),
            psychology_depth=data.get("psychology_depth", 50),
            use_video_patterns=data.get("use_video_patterns", True),
            video_pattern_preference=data.get("video_pattern_preference", []),
        )

    def to_dict(self) -> Dict:
        """パラメータを辞書に変換する。"""
        return {
            "enabled": self.enabled,
            "base_intensity": self.base_intensity,
            "sensory_weights": self.sensory_weights.copy(),
            "pace_ratios": self.pace_ratios.copy(),
            "metaphor_density": self.metaphor_density,
            "psychology_depth": self.psychology_depth,
            "use_video_patterns": self.use_video_patterns,
            "video_pattern_preference": self.video_pattern_preference.copy(),
        }

    @classmethod
    def default_for_intensity(cls, intensity: int) -> "EroticParameters":
        """指定された強度に応じたデフォルトパラメータを生成する。

        Args:
            intensity: 0-5の強度

        Returns:
            強度に応じたデフォルトパラメータ
        """
        params = cls()

        if intensity == 0:
            params.enabled = False
            return params

        params.enabled = True
        params.base_intensity = intensity

        if intensity >= 4:
            params.metaphor_density = 80
            params.psychology_depth = 85
            params.sensory_weights = {
                "touch": 95,
                "breath": 90,
                "sound": 85,
                "scent": 80,
                "gaze": 60,
                "taste": 50,
            }
            params.pace_ratios = {"build": 4, "peak": 3, "afterglow": 3}
        elif intensity >= 3:
            params.metaphor_density = 60
            params.psychology_depth = 65
            params.sensory_weights = {
                "touch": 85,
                "breath": 80,
                "sound": 70,
                "scent": 70,
                "gaze": 55,
                "taste": 35,
            }
            params.pace_ratios = {"build": 3, "peak": 2, "afterglow": 2}
        else:
            params.metaphor_density = 40
            params.psychology_depth = 45
            params.sensory_weights = {
                "touch": 70,
                "breath": 65,
                "sound": 60,
                "scent": 50,
                "gaze": 45,
                "taste": 25,
            }
            params.pace_ratios = {"build": 2, "peak": 1, "afterglow": 2}

        return params