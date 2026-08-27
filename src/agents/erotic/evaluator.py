"""
erotic/evaluator.py - 官能品質評価モジュール
"""

from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field


class EroticQualityReport(BaseModel):
    """官能品質評価レポート"""

    overall_score: float = Field(..., ge=0.0, le=100.0, description="総合スコア")
    sensuality_score: float = Field(..., ge=0.0, le=100.0, description="感覚的要素スコア")
    emotional_score: float = Field(..., ge=0.0, le=100.0, description="感情的要素スコア")
    psychological_score: float = Field(..., ge=0.0, le=100.0, description="心理的要素スコア")
    technical_score: float = Field(..., ge=0.0, le=100.0, description="技術的要素スコア")
    details: Dict[str, Any] = Field(default_factory=dict, description="詳細な評価項目")


class EroticQualityScorer:
    """官能品質を評価するスコアラー"""

    def __init__(self):
        # キー�ーワードベースのスコアリング用�辞書（実際には外部ファイルから読み込むか、より複�雑なロジックを使用）
        self.quality_keywords = {
            "sensory": [
                "熱",
                "温もり",
                "冷たさ",
                "����らか",
                "����さ",
                "����らか",
                "ざらつき",
                "����り",
                "����き",
                "����い",
                "香り",
                "味",
                "����",
                "����",
                "����",
                "指先",
                "����",
                "����",
                "息",
                "����息",
                "����動",
                "����",
                "震え",
                "����れ",
                "電流",
                "火照り",
                "����",
                "����",
                "��������",
                "体����",
            ],
            "emotional": [
                "愛おしい",
                "愛しい",
                "切ない",
                "����しい",
                "����しい",
                "幸せ",
                "恐ろしい",
                "不安",
                "安心",
                "信頼",
                "裏切り",
                "��������",
                "独占欲",
                "����着",
                "����身",
                "��������",
                "許し",
                "受容",
                "共感",
                "同情",
                "����れ",
                "����敬",
                "��������",
            ],
            "psychological": [
                "支配",
                "服従",
                "従����",
                "反抗",
                "����服",
                "解放",
                "束����",
                "自由",
                "罪悪感",
                "背徳",
                "禁����",
                "��������",
                "����れ",
                "清らか",
                "����ら",
                "恥����",
                "����り",
                "プライド",
                "自����心",
                "自我",
                "自我��������",
                "自我����失",
                "自我統合",
            ],
        }

    def score(self, text: str) -> EroticQualityReport:
        """score_quality のエイリアス。"""
        return self.score_quality(text)

    def score_quality(self, text: str) -> EroticQualityReport:
        """
        テキストの官能品質を評価する

        Args:
            text: 評価対象のテキスト

        Returns:
            評価レポート
        """
        if not text:
            return EroticQualityReport(
                overall_score=0.0,
                sensuality_score=0.0,
                emotional_score=0.0,
                psychological_score=0.0,
                technical_score=0.0,
            )

        text_lower = text.lower()
        total_chars = len(text)

        # 各カテゴリのスコアを計算（簡易実装）
        sensuality_score = self._score_category(
            text_lower, self.quality_keywords.get("sensory", []), total_chars
        )
        emotional_score = self._score_category(
            text_lower, self.quality_keywords.get("emotional", []), total_chars
        )
        psychological_score = self._score_category(
            text_lower, self.quality_keywords.get("psychological", []), total_chars
        )

        # � 技術的スコアは文章構造などから評価（簡易実装）
        technical_score = self._score_technical(text, total_chars)

        # 総合スコアは重み付き平均
        overall_score = (
            sensuality_score * 0.3
            + emotional_score * 0.3
            + psychological_score * 0.2
            + technical_score * 0.2
        )

        return EroticQualityReport(
            overall_score=min(100.0, max(0.0, overall_score)),
            sensuality_score=min(100.0, max(0.0, sensuality_score)),
            emotional_score=min(100.0, max(0.0, emotional_score)),
            psychological_score=min(100.0, max(0.0, psychological_score)),
            technical_score=min(100.0, max(0.0, technical_score)),
            details={
                "text_length": total_chars,
                "sensuality_matches": self._count_matches(
                    text_lower, self.quality_keywords.get("sensory", [])
                ),
                "emotional_matches": self._count_matches(
                    text_lower, self.quality_keywords.get("emotional", [])
                ),
                "psychological_matches": self._count_matches(
                    text_lower, self.quality_keywords.get("psychological", [])
                ),
            },
        )

    def _score_category(self, text: str, keywords: List[str], total_chars: int) -> float:
        """特定のカテゴリのキー�ーワードマッチに基づいてスコアを計算"""
        if not keywords or total_chars == 0:
            return 0.0

        matches = self._count_matches(text, keywords)
        # キー�ーワード密度に基づいてスコアを計算（0-100の�範�囲に正規化）
        density = matches / max(total_chars, 1) * 1000  # 文字1000あたりのマッチ数
        return min(100.0, density * 10)  # 適切なスケーリング

    def _score_technical(self, text: str, total_chars: int) -> float:
        """技術的�側面（文章構造、読みやすさなど）を評価"""
        if total_chars == 0:
            return 0.0

        # 簡易的な技術的スコア計算
        sentences = text.split("。")
        avg_sentence_length = sum(len(s) for s in sentences) / max(len(sentences), 1)

        # 適切な文の長さ（20-50文字）を基準にスコアリング
        if 20 <= avg_sentence_length <= 50:
            length_score = 100.0
        elif avg_sentence_length < 20:
            length_score = avg_sentence_length / 20 * 100.0
        else:
            length_score = max(50.0, 100.0 - (avg_sentence_length - 50) * 0.5)

        # �� 段落構造の評価
        paragraphs = text.split("\n\n")
        para_score = 100.0 if len(paragraphs) >= 1 else 50.0

        return (length_score + para_score) / 2

    def _count_matches(self, text: str, keywords: List[str]) -> int:
        """テキスト内のキー�ーワードマッチ数をカウント"""
        if not text or not keywords:
            return 0

        count = 0
        for keyword in keywords:
            count += text.count(keyword)
        return count
