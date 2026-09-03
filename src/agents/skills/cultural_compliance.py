# src/agents/skills/cultural_compliance.py
"""文化的コンプライアンスチェックスキル（サンプル実装）"""
from typing import Any
from src.agents.skill_base import SkillAgent
from src.agents.orchestrator import AgentContext, AgentResult


class CulturalComplianceChecker(SkillAgent):
    """地域別の文化的適切性をチェックするスキル"""

    def __init__(self, *args, strict_mode: bool = True, regions: list[str] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.strict_mode = strict_mode
        self.regions = regions or ["JP", "US", "KR"]
        # 実際の実装では、地域別のタブー語彙・表現データベースを読み込む

    async def execute(self, ctx: AgentContext) -> AgentResult:
        """原稿の文化的適切性をチェック"""
        drafted_text = ctx.artifacts.get("drafted_text", "")
        issues = []

        # 簡易実装: 地域別NGワードチェック
        ng_words = {
            "JP": ["差別用語1", "差別用語2"],
            "US": ["offensive_term1", "offensive_term2"],
            "KR": ["차별용어1", "차별용어2"],
        }

        for region in self.regions:
            for word in ng_words.get(region, []):
                if word in drafted_text:
                    issues.append({
                        "region": region,
                        "type": "cultural_sensitivity",
                        "message": f"地域 {region} で不適切な表現が検出されました: {word}",
                        "severity": "high" if self.strict_mode else "medium",
                    })

        if issues:
            return AgentResult(
                next_agent=None,
                artifacts={
                    "cultural_compliance": "failed",
                    "issues": issues,
                },
                error="Cultural compliance issues detected" if self.strict_mode else None,
            )

        return AgentResult(
            next_agent=None,
            artifacts={"cultural_compliance": "passed"},
        )