import re
from typing import Optional

class DialogueExtractor:
    """小説本文からセリフと話者を抽出するクラス"""

    def extract_dialogues(self, text: str) -> list[dict]:
        """本文からカギ括弧のセリフと、直前のト書きから話者を抽出する"""
        dialogues = []
        # シンプルなカギ括弧抽出（実際にはもう少し複雑なロジックが必要）
        pattern = r"「(.*?)」"
        matches = re.finditer(pattern, text)

        for match in matches:
            dialogue = match.group(1)
            # ト書きの特定ロジック（簡易版）
            preceding_text = text[:match.start()]
            speaker = self._estimate_speaker(preceding_text)
            dialogues.append({"dialogue": dialogue, "speaker": speaker})

        return dialogues

    def _estimate_speaker(self, preceding_text: str) -> Optional[str]:
        """直前のト書きから話者を推定する"""
        lines = preceding_text.splitlines()
        if not lines:
            return None
        match = re.search(r"(.*?)(?:は|が)言った。", lines[-1])
        if match:
            return match.group(1).strip()
        return None
