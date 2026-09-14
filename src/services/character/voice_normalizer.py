import re
from src.services.character.voice_linter import VoiceLinter
from src.models.character_voice_profile import CharacterVoiceProfile

class VoiceNormalizer:
    """セリフの自動修復サービス"""

    def __init__(self):
        self.linter = VoiceLinter()

    def normalize(self, dialogue: str, profile: CharacterVoiceProfile) -> str:
        errors = self.linter.check(dialogue, profile)
        if not errors:
            return dialogue
        
        # 簡易的な修復ロジック（辞書ベース）
        # 本番ではLLMによる修復を呼び出す
        return self._simple_fix(dialogue, profile)

    def _simple_fix(self, dialogue: str, profile: CharacterVoiceProfile) -> str:
        # 一人称の単純置換例
        for p in profile.first_person:
            if "私" in dialogue:
                dialogue = dialogue.replace("私", p)
                break
        
        # 語尾の単純置換（簡易実装）
        if profile.endings:
            # プロファイルで設定されている最初の語尾を採用
            target_ending = profile.endings[0].replace("〜", "")
            
            # 既存の語尾を判定（簡易的なもの）
            known_endings = [e.replace("〜", "") for e in profile.endings]
            
            # 文末が指定された語尾パターンで終わっていない場合のみ置換
            if not any(dialogue.endswith(e) for e in known_endings):
                # 句点を除去して語尾を追加（既存の語尾っぽいものを除外）
                # 本当はより高度な形態素解析が必要
                dialogue = re.sub(r'([。！？])$', '', dialogue) + target_ending
                
        return dialogue
