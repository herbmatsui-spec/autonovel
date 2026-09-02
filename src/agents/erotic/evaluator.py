"""
erotic/evaluator.py - 官能品質評価モジュール (Clean UTF-8 & LLM-as-a-Judge 対応)
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field


class EroticQualityReport(BaseModel):
    """官能品質評価レポート"""

    overall_score: float = Field(..., ge=0.0, le=100.0, description="総合スコア (0-100)")
    sensuality_score: float = Field(..., ge=0.0, le=100.0, description="感覚的要素スコア (0-100)")
    emotional_score: float = Field(..., ge=0.0, le=100.0, description="感情的要素スコア (0-100)")
    psychological_score: float = Field(..., ge=0.0, le=100.0, description="心理的要素スコア (0-100)")
    technical_score: float = Field(..., ge=0.0, le=100.0, description="技術的要素スコア (0-100)")
    details: dict[str, Any] = Field(default_factory=dict, description="詳細な評価項目・講評")


class EroticQualityScorer:
    """官能品質を評価するスコアラー (キーワード評価 ＋ LLM-as-a-Judge)."""

    def __init__(self):
        # クリーンな日本語官能ボキャブラリ辞書
        self.quality_keywords = {
            "sensory": [
                "熱", "温もり", "冷たさ", "柔らか", "硬さ", "滑らか", "ざらつき", "湿り", "渇き",
                "甘い", "香り", "匂い", "味", "感触", "肌触り", "指先", "唇", "吐息", "息遣い",
                "鼓動", "脈動", "震え", "痺れ", "電流", "火照り", "熱気", "汗", "摩擦", "体温",
                "締めつけ", "疼き", "蠢き", "快感", "昂ぶり",
            ],
            "emotional": [
                "愛おし", "愛し", "切な", "狂おし", "恋し", "愛おしい", "愛しい", "切ない", "狂おしい",
                "恋しい", "幸せ", "恐ろしい", "不安", "安心", "信頼", "裏切り", "嫉妬", "独占欲",
                "執着", "献身", "情熱", "許し", "受容", "共感", "同情", "憧れ", "崇拝", "慕情", "焦燥",
            ],
            "psychological": [
                "支配", "服従", "従順", "反抗", "屈服", "解放", "束縛", "自由", "罪悪感", "背徳",
                "禁断", "快楽", "羞恥", "清らか", "淫ら", "誇り", "プライド", "自尊心", "自我",
                "自我崩壊", "自我喪失", "自我統合", "葛藤", "耽溺",
            ],
        }

    def score(self, text: str) -> EroticQualityReport:
        """score_quality のエイリアス"""
        return self.score_quality(text)

    def score_quality(self, text: str) -> EroticQualityReport:
        """
        テキストの官能品質をキーワードベースで高速評価する (フォールバック用).

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

        sensuality_score = self._score_category(
            text_lower, self.quality_keywords.get("sensory", []), total_chars
        )
        emotional_score = self._score_category(
            text_lower, self.quality_keywords.get("emotional", []), total_chars
        )
        psychological_score = self._score_category(
            text_lower, self.quality_keywords.get("psychological", []), total_chars
        )
        technical_score = self._score_technical(text, total_chars)

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
                "eval_method": "keyword_heuristic",
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

    def evaluate_quality_with_llm(
        self,
        text: str,
        llm_adapter: Any = None,
    ) -> EroticQualityReport:
        """
        LLM-as-a-Judge を用いて、多層的な官能・心理描写品質を精密に評価する.
        LLM呼び出し失敗時は自動で `score_quality` へフォールバックする.
        """
        if not text or not text.strip():
            return self.score_quality(text)

        if llm_adapter is None:
            try:
                from src.services.llm.factory import get_llm_adapter
                llm_adapter = get_llm_adapter()
            except Exception:
                return self.score_quality(text)

        system_prompt = (
            "あなたはプロのライトノベル・官能小説編集者です。\n"
            "提示された小説テキストの官能・感情描写品質を、以下の4軸（各0-100点）および総合スコアで厳格に審査してください。\n\n"
            "1. sensuality_score: 身体感覚（触覚・体温・吐息・鼓動など）の臨場感\n"
            "2. emotional_score: 心情の機微、切なさ、愛おしさ、葛藤の表現力\n"
            "3. psychological_score: 背徳感、支配/服従、心理的変化の深さ\n"
            "4. technical_score: リズム感、テンポ、語彙の豊かさ、文章構成力\n"
            "5. overall_score: 総合スコア\n\n"
            "必ず以下の JSON 形式のみで返答してください:\n"
            '{"overall_score": 85.0, "sensuality_score": 90.0, "emotional_score": 80.0, "psychological_score": 85.0, "technical_score": 85.0, "details": {"feedback": "簡潔な講評"}}'
        )

        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "erotic_quality_report",
                "schema": EroticQualityReport.model_json_schema(),
            },
        }

        try:
            raw_json = llm_adapter.generate(
                prompt=f"【評価対象テキスト】\n{text[:3000]}",
                system_prompt=system_prompt,
                temperature=0.1,
                response_format=response_format,
            )
            # コードブロック除去
            cleaned = raw_json.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            elif cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            
            data = json.loads(cleaned.strip())
            report = EroticQualityReport.model_validate(data)
            if "eval_method" not in report.details:
                report.details["eval_method"] = "llm_as_a_judge"
            return report
        except Exception:
            # フォールバック
            return self.score_quality(text)

    def _score_category(self, text: str, keywords: list[str], total_chars: int) -> float:
        """特定のカテゴリのキーワードマッチに基づいてスコアを計算"""
        if not keywords or total_chars == 0:
            return 0.0

        matches = self._count_matches(text, keywords)
        density = matches / max(total_chars, 1) * 1000  # 文字1000あたりのマッチ数
        return min(100.0, density * 10)

    def _score_technical(self, text: str, total_chars: int) -> float:
        """技術的側面（文章構造、読みやすさなど）を評価"""
        if total_chars == 0:
            return 0.0

        sentences = [s for s in text.split("。") if s.strip()]
        avg_sentence_length = sum(len(s) for s in sentences) / max(len(sentences), 1)

        if 20 <= avg_sentence_length <= 50:
            length_score = 100.0
        elif avg_sentence_length < 20:
            length_score = avg_sentence_length / 20 * 100.0
        else:
            length_score = max(50.0, 100.0 - (avg_sentence_length - 50) * 0.5)

        paragraphs = [p for p in text.split("\n\n") if p.strip()]
        para_score = 100.0 if len(paragraphs) >= 1 else 50.0

        return (length_score + para_score) / 2

    def _count_matches(self, text: str, keywords: list[str]) -> int:
        """テキスト内のキーワードマッチ数をカウント"""
        if not text or not keywords:
            return 0

        count = 0
        for keyword in keywords:
            count += text.count(keyword)
        return count
