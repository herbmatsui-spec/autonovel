from dataclasses import dataclass, field
from typing import List, Literal, Optional

try:
    from config.erotic_parameters import EroticParameters
except ImportError:
    EroticParameters = None


@dataclass
class EroticBeat:
    phase: Literal["build", "peak", "afterglow"]
    desire_level: int  # 0-100
    sensory_focus: List[str]  # ["touch", "scent", "breath", "gaze", "sound"]
    consent_state: str = "implicit"
    sub_beats: List["EroticBeat"] = field(default_factory=list)

    def validate(self) -> bool:
        """desire_levelが0-100の範囲かつconsent_stateが有効かを検証する"""
        valid_consent = self.consent_state in ("explicit", "implicit", "established")
        valid_level = 0 <= self.desire_level <= 100
        return valid_consent and valid_level


@dataclass
class EroticCurve:
    beats: List[EroticBeat]
    target_intensity: int  # 0-5

    def get_peak_beat(self) -> Optional[EroticBeat]:
        """peakフェーズのbeatを返す。存在しなければNone。"""
        for beat in self.beats:
            if beat.phase == "peak":
                return beat
        return None

    def get_all_beats(self) -> List[EroticBeat]:
        """メインビートとサブビートをすべて展開して返す"""
        all_beats = []
        for beat in self.beats:
            all_beats.append(beat)
            if beat.sub_beats:
                all_beats.extend(beat.sub_beats)
        return all_beats

    @staticmethod
    def create_default(intensity: int = 2) -> "EroticCurve":
        """強度に応じた3フェーズ曲線を生成する。強度4以上ではサブビートを追加"""
        base_desire = min(intensity * 18 + 15, 95)
        peak_desire = min(intensity * 20, 100)

        beats = [
            EroticBeat(
                phase="build",
                desire_level=base_desire - 25,
                sensory_focus=["gaze", "scent", "breath"],
                consent_state="implicit",
            )
        ]

        if intensity >= 4:
            beats[0].sub_beats = [
                EroticBeat(
                    phase="build",
                    desire_level=base_desire - 10,
                    sensory_focus=["touch", "gaze"],
                    consent_state="implicit",
                ),
                EroticBeat(
                    phase="build",
                    desire_level=base_desire,
                    sensory_focus=["touch", "breath", "scent"],
                    consent_state="implicit",
                ),
            ]

        if intensity >= 3:
            peak_tremolo_count = min(intensity - 2, 3)
            peak_beats = []
            for i in range(peak_tremolo_count):
                tremolo_desire = peak_desire - 5 * (peak_tremolo_count - i - 1)
                peak_beats.append(
                    EroticBeat(
                        phase="peak",
                        desire_level=tremolo_desire,
                        sensory_focus=["touch", "breath", "sound", "scent"],
                        consent_state="explicit",
                    )
                )
            beats.append(
                EroticBeat(
                    phase="peak",
                    desire_level=peak_desire,
                    sensory_focus=["touch", "breath", "sound", "gaze", "scent"],
                    consent_state="explicit",
                    sub_beats=peak_beats if peak_tremolo_count > 0 else [],
                )
            )
        else:
            beats.append(
                EroticBeat(
                    phase="peak",
                    desire_level=peak_desire,
                    sensory_focus=["touch", "breath", "sound"],
                    consent_state="explicit",
                )
            )

        afterglow_desire = 20 + intensity * 2
        afterglow = EroticBeat(
            phase="afterglow",
            desire_level=min(afterglow_desire, 40),
            sensory_focus=["touch", "gaze"],
            consent_state="established",
        )

        if intensity >= 4:
            afterglow.sub_beats = [
                EroticBeat(
                    phase="afterglow",
                    desire_level=min(afterglow_desire - 10, 30),
                    sensory_focus=["touch", "breath"],
                    consent_state="established",
                )
            ]
        beats.append(afterglow)

        return EroticCurve(beats=beats, target_intensity=intensity)

    @staticmethod
    def create_from_parameters(params: "EroticParameters") -> "EroticCurve":
        """EroticParametersから動的に曲線を生成する。

        Args:
            params: EroticParametersインスタンス

        Returns:
            パラメータに基づいたEroticCurve
        """
        if EroticParameters is None:
            return EroticCurve.create_default(params.base_intensity)

        if not params.enabled or params.base_intensity == 0:
            return EroticCurve.create_default(0)

        intensity = params.base_intensity
        build_ratio = params.pace_ratios.get("build", 3)
        peak_ratio = params.pace_ratios.get("peak", 2)
        afterglow_ratio = params.pace_ratios.get("afterglow", 2)

        sorted_senses = params.get_sorted_sensory_priority()

        def get_sensory_focus_for_phase(
            phase: str, default: List[str]
        ) -> List[str]:
            """フェーズとデフォルト感覚から重み付けされた感覚リストを返す"""
            senses = []
            for sense in sorted_senses:
                if sense in default or params.sensory_weights.get(sense, 50) >= 70:
                    senses.append(sense)
            return senses[:5] if len(senses) >= 5 else senses or default

        base_desire = min(intensity * 18 + 15, 95)
        peak_desire = min(intensity * 20, 100)

        build_senses = get_sensory_focus_for_phase(
            "build", ["gaze", "scent", "breath"]
        )
        beats = [
            EroticBeat(
                phase="build",
                desire_level=max(base_desire - 25, 20),
                sensory_focus=build_senses,
                consent_state="implicit",
            )
        ]

        build_count = params.get_beat_count_for_phase("build")
        if build_count > 1 and intensity >= 3:
            sub_builds = []
            for i in range(build_count - 1):
                desire = base_desire - 15 + (10 * i)
                sub_senses = get_sensory_focus_for_phase(
                    "build",
                    ["touch", "breath"] if i % 2 == 0 else ["gaze", "scent"],
                )
                sub_builds.append(
                    EroticBeat(
                        phase="build",
                        desire_level=min(desire, base_desire - 5),
                        sensory_focus=sub_senses,
                        consent_state="implicit",
                    )
                )
            beats[0].sub_beats = sub_builds

        peak_senses = get_sensory_focus_for_phase(
            "peak", ["touch", "breath", "sound", "scent"]
        )
        peak_count = params.get_beat_count_for_phase("peak")

        if peak_count > 1 and intensity >= 3:
            peak_sub_beats = []
            for i in range(peak_count):
                tremolo_desire = peak_desire - (5 * (peak_count - i - 1))
                tremolo_senses = get_sensory_focus_for_phase(
                    "peak",
                    sorted_senses[:4],
                )
                peak_sub_beats.append(
                    EroticBeat(
                        phase="peak",
                        desire_level=max(tremolo_desire, 70),
                        sensory_focus=tremolo_senses,
                        consent_state="explicit",
                    )
                )
            beats.append(
                EroticBeat(
                    phase="peak",
                    desire_level=peak_desire,
                    sensory_focus=peak_senses,
                    consent_state="explicit",
                    sub_beats=peak_sub_beats,
                )
            )
        else:
            beats.append(
                EroticBeat(
                    phase="peak",
                    desire_level=peak_desire,
                    sensory_focus=peak_senses,
                    consent_state="explicit",
                )
            )

        afterglow_senses = get_sensory_focus_for_phase(
            "afterglow", ["touch", "gaze"]
        )
        afterglow_desire = min(20 + intensity * 2, 40)
        afterglow = EroticBeat(
            phase="afterglow",
            desire_level=afterglow_desire,
            sensory_focus=afterglow_senses,
            consent_state="established",
        )

        afterglow_count = params.get_beat_count_for_phase("afterglow")
        if afterglow_count > 1 and intensity >= 3:
            sub_afterglow = []
            for i in range(afterglow_count - 1):
                sub_afterglow.append(
                    EroticBeat(
                        phase="afterglow",
                        desire_level=max(afterglow_desire - 10 * (i + 1), 15),
                        sensory_focus=get_sensory_focus_for_phase(
                            "afterglow", ["touch", "breath"]
                        ),
                        consent_state="established",
                    )
                )
            afterglow.sub_beats = sub_afterglow

        beats.append(afterglow)

        return EroticCurve(beats=beats, target_intensity=intensity)

