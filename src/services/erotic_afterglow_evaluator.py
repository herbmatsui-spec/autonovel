"""
src/services/erotic_afterglow_evaluator.py
afterglow フェーズ専用の品質評価サービス
"""
from typing import List, Tuple

from config.erotic_thresholds import AFTERGLOW_MIN_CHARS, AFTERGLOW_MIN_PARAGRAPHS


class AfterglowEvaluator:
    """afterglow フェーズの質評価を行う。"""

    EMOTIONAL_SETTLING_KEYWORDS = ["沈静", "静けさ", "余韻", "穏やか", "温もり", "安らぎ", "沈降", "静まる"]
    DISTANCE_RECONFIRM_KEYWORDS = ["距離", "近了", "確認", "並べ", "隣", "寄り添う", "離れた"]
    FOREShadow_KEYWORDS = ["次", "話", "伏線", "予感", "接下来", "明らかになる", "待ち望む"]

    def count_paragraphs(self, text: str) -> int:
        """空行で区切られた段落数をカウントする。"""
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        return len(paragraphs)

    def check_emotional_settling(self, text: str) -> bool:
        """感情の沈降表現が含まれているかチェックする。"""
        return any(kw in text for kw in self.EMOTIONAL_SETTLING_KEYWORDS)

    def check_distance_reconfirm(self, text: str) -> bool:
        """心理的・物理的距離の再確認表現が含まれているかチェックする。"""
        return any(kw in text for kw in self.DISTANCE_RECONFIRM_KEYWORDS)

    def check_foreshadow(self, text: str) -> bool:
        """次話への伏線が含まれているかチェックする。"""
        return any(kw in text for kw in self.FOREShadow_KEYWORDS)

    def evaluate(self, text: str) -> Tuple[bool, List[str]]:
        """
        afterglow テキストを多角的に評価する。

        Returns:
            (is_acceptable, issues): 評価結果と問題リスト
        """
        issues: List[str] = []

        paragraph_count = self.count_paragraphs(text)
        if paragraph_count < AFTERGLOW_MIN_PARAGRAPHS:
            issues.append(f"段落数が不足: {paragraph_count}/{AFTERGLOW_MIN_PARAGRAPHS}")

        char_count = len(text)
        if char_count < AFTERGLOW_MIN_CHARS:
            issues.append(f"文字数が不足: {char_count}/{AFTERGLOW_MIN_CHARS}")

        if not self.check_emotional_settling(text):
            issues.append("感情の沈降表現（余韻・穏やか・温もり等）が含まれていません")

        if not self.check_distance_reconfirm(text):
            issues.append("心理的・物理的距離の再確認表現が含まれていません")

        if not self.check_foreshadow(text):
            issues.append("次話への伏線が含まれていません")

        return len(issues) == 0, issues
