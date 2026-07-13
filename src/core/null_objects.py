from typing import Any, Dict, List, Optional, Tuple

from src.agents.debate import NullDebateAgent
from src.models import (
    ForeshadowingAudit,
    HegemonyAuditResult,
    LogicalAuditIssueList,
    LogicalAuditResult,
    WorldState,
)


class NullMarketingAgent:
    async def generate_marketing_pack(self, book_title: str, synopsis: str, latest_ep: int, **kwargs) -> Optional[Dict[str, Any]]:
        return None

    async def generate_titles(self, genre: str, keywords: str) -> List[str]:
        return ["覇権の始まり", "追放された最強者", "全てを超えし者"]

    async def analyze_style_dna(self, sample_text: str) -> Dict[str, Any]:
        return {"name": "分析失敗", "instruction": "", "score": 0, "analysis": ""}

class NullLogicalAuditor:
    async def audit_plot_as_issues(
        self, book_id: int, branch_id: int, ep_num: int,
        plot_bp: str, script: str = "", cheat_scale: int = 4
    ) -> LogicalAuditIssueList:
        """[Null Object] 常に整合性OKを返す"""
        return LogicalAuditIssueList(is_consistent=True)

    async def generate_critic_feedback(self, issue_list: Any, draft_content: str, blueprint: str) -> Any:
        from src.models.audit import CriticFeedback
        return CriticFeedback(has_critical_issues=False)

    async def audit_plot(self, book_id: int, branch_id: int, ep_num: int, plot_bp: str, script: str) -> LogicalAuditResult:
        return LogicalAuditResult(is_consistent=True)

    async def audit_plot_integrity(self, branch_id: int, synopsis: str, world_settings_json: str, reporter=None) -> HegemonyAuditResult:
        return HegemonyAuditResult(is_consistent=True, conflict_report="監査に失敗しました（Null Object）")

    async def check_misunderstanding_inflation(self, book_id: int, current_gap: str, prev_gap: str) -> str:
        return ""

    async def horror_progression_audit(
        self,
        book_id: int,
        ep_num: int,
        mystery_schedule: list,
        thinning_rate: float,
        total_eps: int = 50,
    ) -> LogicalAuditResult:
        return LogicalAuditResult(is_consistent=True)

    async def audit_foreshadowing_payoff(self, book_id: int, ep_num: int, content: str) -> ForeshadowingAudit:
        return ForeshadowingAudit(is_recovered=True)

    async def lightweight_audit_world_state(self, current: WorldState, previous: Optional[WorldState]) -> LogicalAuditResult:
        return LogicalAuditResult(is_consistent=True)

    async def audit_magic_cost(self, magic_cost_and_taboo: str, plot_blueprint: str) -> bool:
        return True

class NullInternalLogicValidator:
    async def validate_misunderstanding_flow(self, content: str, gap_desc: str) -> Tuple[bool, List[str]]:
        return True, []

class NullPlotIntegrityMonitor:
    def extract_keywords(self, blueprint: str) -> List[str]:
        return []

    async def check_integrity(self, keywords: List[str], blueprint: str, content: str, threshold: float = 0.8) -> Tuple[bool, float, List[str]]:
        return True, 1.0, []

    async def run_constraint_unit_tests(self, content: str, constraints: List[Any]) -> Tuple[bool, List[Dict[str, Any]]]:
        return True, []

    async def audit_setting_causality(self, content: str, world_settings: str, plot_blueprint: str) -> Tuple[bool, str, List[Dict[str, Any]]]:
        return True, "不整合なし", []

    async def audit_blueprint_causality(self, blueprint: str, world_settings: str) -> Tuple[bool, str, str]:
        return True, "不整合なし", ""

    async def AntagonistIQAudit(self, blueprint: str, world_settings: str, antagonist_profile: str, reporter=None) -> Tuple[bool, str, str]:
        return True, "不整合なし", ""

class NullAbilityConsistencyChecker:
    async def audit_ability_consistency(
        self, blueprint: str, world_settings_str: str, characters_str: str
    ) -> Tuple[bool, str, str]:
        return True, "不整合なし", ""

class NullFastPlotScreener:
    async def screen_plot(self, plot_text: str, constraints: List[str] = None) -> Tuple[bool, str]:
        return True, "合格"

    def pick_best(self, variants: Dict[str, Any]) -> Tuple[Optional[str], Optional[Any]]:
        if not variants:
            return None, None
        first_key = list(variants.keys())[0]
        return first_key, variants[first_key]

class NullWriterAgent:
    async def analyze_and_import_chapter(self, book_id: int, ep_num: int, import_text: str, do_refine: bool = True) -> Dict[str, Any]:
        return {"status": "success"}

class NullEngine:
    def __init__(self):
        self.writer = NullWriterAgent()
        self.marketing = NullMarketingAgent()
        self.auditor = NullLogicalAuditor()

        from src.core.system_plugin_loader import SystemPluginLoader
        DebateAgentClass = SystemPluginLoader.get_plugin_class("debate_agent", default_class=NullDebateAgent)
        self.debate = DebateAgentClass()
