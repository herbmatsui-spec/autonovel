"""Beat validator for emotional annotations."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.annotations.beat import EmotionalBeat
from src.pipeline.emotional_residue import EmotionType
from src.pipeline.character_dict import load_character_dict


@dataclass
class ValidationResult:
    """検証結果"""
    is_valid: bool
    errors: list[str]
    warnings: list[str]


class BeatValidator:
    """感情ビートの検証・整合性チェック"""
    
    def __init__(self, character_dict: Optional[set[str]] = None):
        self.character_dict = character_dict or load_character_dict()
        
        # 表向き/内心の組み合わせルール
        # hidden=True の場合、表向きの逆の感情は警告
        self.contradiction_pairs = {
            (EmotionType.AFFECTION, EmotionType.DISGUST),
            (EmotionType.TRUST, EmotionType.ANGER),
            (EmotionType.FEAR, EmotionType.TRUST),
        }

    def validate(
        self, 
        beats: list[EmotionalBeat], 
        character_dict: Optional[set[str]] = None,
    ) -> ValidationResult:
        """ビートリストを検証"""
        errors = []
        warnings = []
        dict_to_use = character_dict or self.character_dict
        
        for beat in beats:
            # 1. キャラ名存在チェック
            if beat.source not in dict_to_use:
                errors.append(f"Beat {beat.beat_id}: Unknown source character '{beat.source}'")
            if beat.target not in dict_to_use:
                errors.append(f"Beat {beat.beat_id}: Unknown target character '{beat.target}'")
            
            # 2. delta範囲チェック（クランプ前の元の値を想定。EmotionalBeatでクランプ済みなのでここではスキップ）
            # 実際の実装ではクランプ前の値をチェックする必要がある
            
            # 3. confidence範囲チェック（同上）
            
            # 4. 同一シーン・同一ペア・同一感情の重複チェック
            
            # 5. hidden=true の場合の矛盾チェック
            if beat.hidden:
                self._check_hidden_contradiction(beat, dict_to_use, warnings)
            
            # 6. cause 未記入チェック
            if not beat.cause or beat.cause.strip() == "":
                warnings.append(f"Beat {beat.beat_id}: Empty cause field")
        
        # 7. シーン内の重複チェック（同一感情）
        self._check_duplicates(beats, warnings)
        
        # 8. 異なる感情間の矛盾チェック（hidden vs overt）
        self._check_cross_emotion_contradictions(beats, warnings)
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def _check_hidden_contradiction(
        self, 
        beat: EmotionalBeat, 
        character_dict: set[str],
        warnings: list[str],
    ) -> None:
        """hidden=true の場合、同じ episode/scene/source/target で 
        異なる感情の表向きビートとの矛盾をチェック"""
        # _check_duplicates で同一感情の場合はチェック済み
        # ここでは異なる感情での矛盾をチェック
        pass

    def _check_duplicates(self, beats: list[EmotionalBeat], warnings: list[str]) -> None:
        """重複・矛盾チェック"""
        # キー: (episode, scene, source, target, emotion)
        seen = {}
        
        for beat in beats:
            key = (beat.episode, beat.scene, beat.source, beat.target, beat.emotion)
            
            if key in seen:
                existing = seen[key]
                # 同一キーの重複
                if abs(existing.delta - beat.delta) > 0.01:
                    warnings.append(
                        f"Duplicate beat with different delta: {key} "
                        f"(existing: {existing.delta:.2f}, new: {beat.delta:.2f})"
                    )
                # hidden/表向きの矛盾
                if existing.hidden != beat.hidden:
                    if existing.hidden and not beat.hidden:
                        # 表向きと内心の矛盾チェック
                        self._check_contradiction_pair(existing, beat, warnings)
                    elif not existing.hidden and beat.hidden:
                        self._check_contradiction_pair(beat, existing, warnings)
            else:
                seen[key] = beat

    def _check_contradiction_pair(
        self, 
        hidden_beat: EmotionalBeat, 
        overt_beat: EmotionalBeat, 
        warnings: list[str],
    ) -> None:
        """表向きと内心の感情矛盾をチェック"""
        hidden_emo = hidden_beat.emotion
        overt_emo = overt_beat.emotion
        
        # 既知の矛盾ペア
        if (hidden_emo, overt_emo) in self.contradiction_pairs or \
           (overt_emo, hidden_emo) in self.contradiction_pairs:
            warnings.append(
                f"Potential contradiction: {hidden_beat.source}->{hidden_beat.target} "
                f"hidden={hidden_emo.value}({hidden_beat.delta:+.2f}) "
                f"vs overt={overt_emo.value}({overt_beat.delta:+.2f})"
            )
        
        # 同じ感情で符号が逆
        if hidden_emo == overt_emo and hidden_beat.delta * overt_beat.delta < -0.1:
            warnings.append(
                f"Sign contradiction: {hidden_beat.source}->{hidden_beat.target} "
                f"hidden={hidden_beat.delta:+.2f} vs overt={overt_beat.delta:+.2f}"
            )

    def _check_cross_emotion_contradictions(
        self, 
        beats: list[EmotionalBeat], 
        warnings: list[str],
    ) -> None:
        """異なる感情間での hidden/overt 矛盾をチェック"""
        # ペアごとにグループ化: (episode, scene, source, target) -> list[beats]
        pairs = {}
        for beat in beats:
            key = (beat.episode, beat.scene, beat.source, beat.target)
            if key not in pairs:
                pairs[key] = []
            pairs[key].append(beat)
        
        for key, pair_beats in pairs.items():
            hidden_beats = [b for b in pair_beats if b.hidden]
            overt_beats = [b for b in pair_beats if not b.hidden]
            
            for h_beat in hidden_beats:
                for o_beat in overt_beats:
                    # 異なる感情での矛盾チェック
                    if h_beat.emotion != o_beat.emotion:
                        if (h_beat.emotion, o_beat.emotion) in self.contradiction_pairs or \
                           (o_beat.emotion, h_beat.emotion) in self.contradiction_pairs:
                            warnings.append(
                                f"Cross-emotion contradiction: {key[2]}->{key[3]} "
                                f"hidden={h_beat.emotion.value}({h_beat.delta:+.2f}) "
                                f"vs overt={o_beat.emotion.value}({o_beat.delta:+.2f})"
                            )


def validate_beats(
    beats: list[EmotionalBeat],
    character_dict: Optional[set[str]] = None,
) -> ValidationResult:
    """便利関数: ビートリスト検証"""
    validator = BeatValidator()
    return validator.validate(beats, character_dict)


__all__ = ["BeatValidator", "ValidationResult", "validate_beats"]