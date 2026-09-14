import re
from src.models.character_voice_profile import CharacterVoiceProfile

class VoiceLinter:
    """セリフの口調ルール違反を検知するクラス"""

    def check(self, dialogue: str, profile: CharacterVoiceProfile) -> list[str]:
        errors = []
        
        # 禁止語チェック
        for word in profile.forbidden_words:
            if word in dialogue:
                errors.append(f"Forbidden word detected: {word}")
        
        # 語尾チェック（簡易実装）
        has_valid_ending = any(dialogue.endswith(ending.replace("〜", "")) for ending in profile.endings)
        if not has_valid_ending:
            errors.append(f"Invalid ending detected. Expected endings: {profile.endings}")
            
        return errors
