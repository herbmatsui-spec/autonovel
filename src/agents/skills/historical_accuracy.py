# src/agents/skills/historical_accuracy.py
"""時代考証チェックスキル（サンプル実装）"""
from typing import Any
from src.agents.skill_base import SkillAgent
from src.agents.orchestrator import AgentContext, AgentResult


class HistoricalAccuracyChecker(SkillAgent):
    """歴史的事実・時代設定の整合性をチェックするスキル"""

    def __init__(self, *args, period: str = "medieval", **kwargs):
        super().__init__(*args, **kwargs)
        self.period = period
        # 実際の実装では、時代別の技術レベル・用語・風俗習慣データベースを読み込む

    async def execute(self, ctx: AgentContext) -> AgentResult:
        """原稿の時代考証をチェック"""
        drafted_text = ctx.artifacts.get("drafted_text", "")
        writing_context = ctx.artifacts.get("writing_context", {})
        world_settings = writing_context.get("world_settings", {})

        issues = []

        # 時代設定の取得
        tech_level = world_settings.get("technology_level", self.period)
        anachronisms = self._get_anachronisms(tech_level)

        # アナクロニズム検出
        for term in anachronisms:
            if term.lower() in drafted_text.lower():
                issues.append({
                    "type": "anachronism",
                    "term": term,
                    "expected_period": tech_level,
                    "message": f"時代設定「{tech_level}」に不適切な用語: {term}",
                    "severity": "high",
                })

        # 歴史的事実との整合性（簡易版）
        if self.period == "edo" and "拳銃" in drafted_text:
            issues.append({
                "type": "historical_inaccuracy",
                "message": "江戸時代設定で拳銃が使用されています（江戸時代末期以降の限定的導入を除く）",
                "severity": "high",
            })

        if issues:
            return AgentResult(
                next_agent=None,
                artifacts={
                    "historical_accuracy": "failed",
                    "issues": issues,
                },
            )

        return AgentResult(
            next_agent=None,
            artifacts={"historical_accuracy": "passed"},
        )

    def _get_anachronisms(self, period: str) -> list[str]:
        """時代に合わない用語リストを返す（簡易版）"""
        anachronism_db = {
            "ancient": ["電話", "自動車", "飛行機", "コンピュータ", "プラスチック", "抗生物質"],
            "medieval": ["電話", "自動車", "飛行機", "コンピュータ", "プラスチック", "抗生物質", "拳銃", "ライフル"],
            "edo": ["電話", "自動車", "飛行機", "コンピュータ", "プラスチック", "抗生物質", "ライフル", "機関銃"],
            "modern": ["蒸気機関", "馬車", "提灯", "着物（日常着として）"],
            "futuristic": [],
        }
        return anachronism_db.get(period, [])