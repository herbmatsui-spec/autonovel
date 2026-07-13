# agents/audit.py
from typing import Any, Dict, List, Optional, Tuple

from src.backend.sharp_edge_preserver import check_edges_preserved
from src.models.audit import LogicalAuditIssueList
from src.models.db import PlotDbModel
from src.models.sharp_edge import SharpEdgeSpec
from src.services.llm_service import LLMService


class FastPlotScreener:
    """プロット快速スクリーニング。Gemini にプロットの妥当性を検証させる。"""
    def __init__(self, llm: LLMService, prompt_manager: Any):
        self.llm = llm
        self.prompt_manager = prompt_manager

    async def screen_plot(self, blueprint: str) -> Tuple[bool, str]:
        prompt = self.prompt_manager.build_fast_plot_screen_prompt(blueprint)
        result = await self.llm.generate_json(purpose="audit", prompt=prompt)
        metadata = result.get("metadata", {})
        return metadata.get("is_valid", True), metadata.get("feedback", "OK")


class AbilityConsistencyChecker:
    """能力整合性チェック"""
    def __init__(self, llm: LLMService, prompt_manager: Any = None):
        self.llm = llm
        self.prompt_manager = prompt_manager

    async def audit_ability_consistency(self, blueprint: str, settings_json: str, characters_json: str) -> Tuple[bool, str, str]:
        if self.prompt_manager is None:
            return True, "OK", ""
        prompt = self.prompt_manager.build_ability_audit_prompt(blueprint, settings_json, characters_json)
        result = await self.llm.generate_json(purpose="audit", prompt=prompt)
        metadata = result.get("metadata", {})
        return metadata.get("is_consistent", True), metadata.get("feedback", "OK"), metadata.get("suggestions", "")


class PlotIntegrityMonitor:
    """プロット整合性モニター（簡易スタブ）"""
    def extract_keywords(self, blueprint: str) -> List[str]:
        return []

    async def check_integrity(self, keywords: List[str], blueprint: str, content: str, threshold: float = 0.7) -> Tuple[bool, float, Any]:
        return True, 1.0, None


class DeAIAuditor:
    """AI感除去監査エージェント"""
    def __init__(self, repo=None, llm: LLMService = None, prompt_manager: Any = None, edge_preserver=None, *args, **kwargs):
        self.repo = repo
        self.llm = llm
        self.prompt_manager = prompt_manager
        self.edge_preserver = edge_preserver  # New parameter for semantic edge preservation

    async def audit(self, content: str, before_content: Optional[str] = None, edges: Optional[List[SharpEdgeSpec]] = None, emotional_hook: Optional[Any] = None) -> Tuple[bool, str]:
        if edges:
            if self.edge_preserver is not None:
                # Semantic mode: use SemanticEdgePreserver for robust detection
                semantic_lost, _ = await self.edge_preserver.check_edges_preserved(
                    before_content or "",
                    content,
                    edges,
                )
                lost = semantic_lost
            else:
                # Legacy string-only mode (backward compatible)
                lost = check_edges_preserved(
                    before_content or "",
                    content,
                    edges,
                )
            if lost:
                lost_types = ", ".join(e.edge_type for e in lost)
                return False, f"以下の角が削られました: {lost_types}"

        if emotional_hook is not None:
            hook_edges = [SharpEdgeSpec(
                edge_type="emotional_hook",
                description=getattr(emotional_hook, "one_line_intent", str(emotional_hook)),
            )]
            if self.edge_preserver is not None:
                semantic_lost, _ = await self.edge_preserver.check_edges_preserved(
                    before_content or "",
                    content,
                    hook_edges,
                )
                lost = semantic_lost
            else:
                lost = check_edges_preserved(
                    before_content or "",
                    content,
                    hook_edges,
                )
            if lost:
                return False, f"刺さりが削られました: {getattr(emotional_hook, 'one_line_intent', '')}"

        if self.prompt_manager is None:
            return True, "OK"
        prompt = self.prompt_manager.build_critic_feedback_prompt(
            issue_list=None, draft_content=content, blueprint=content
        )
        result = await self.llm.generate_json(purpose="audit", prompt=prompt)
        metadata = result.get("metadata", {})
        return metadata.get("is_valid", True), metadata.get("feedback", "OK")



class InternalLogicValidator:
    """内部ロジック(アリバイ・タイムライン・情報非対称)の整合性検証エージェント。

    テスト・簡易利用側は PromptManager と generate_json 呼び出しを
     kwargs 経由で注入できる（LogicalAuditor と同様の設計）。
    """

    def __init__(self, repo: Any = None, llm: Any = None, ctx_mgr: Any = None, pm: Any = None, **kwargs):
        self.repo = repo
        self.ctx_mgr = ctx_mgr
        self.prompt_manager = pm

        # Priority 1: Explicit generate_json provided in kwargs (Common in tests)
        if "generate_json" in kwargs:
            self.llm = kwargs["generate_json"]
        # Priority 2: llm argument provided
        elif llm is not None:
            self.llm = llm
        else:
            self.llm = None

        self.wave_analyzer = None

    async def validate_alibi_and_timeline(self, blueprint: str, script: str) -> Tuple[bool, List[str]]:
        """アリバイとタイムラインの整合性を検証する（スタブ）。"""
        return True, []

    async def check_information_asymmetry(self, past_info: str, current_info: str) -> Tuple[bool, List[str]]:
        """情報の非対称性を検証する（スタブ）。"""
        return True, []


class LogicalAuditor:
    """ロジカル一貫性チェックエージェント"""
    def __init__(self, repo: Any = None, llm: Any = None, ctx_mgr: Any = None, pm: Any = None, **kwargs):
        self.repo = repo
        self.ctx_mgr = ctx_mgr
        self.prompt_manager = pm

        # Priority 1: Explicit generate_json provided in kwargs (Common in tests)
        if "generate_json" in kwargs:
            self.llm = kwargs["generate_json"]
        # Priority 2: llm argument provided
        elif llm is not None:
            self.llm = llm
        else:
            self.llm = None

        self.wave_analyzer = None

    async def generate_critic_feedback(self, issue_list: LogicalAuditIssueList, draft_content: str, blueprint: str) -> str:
        """
        Criticエージェントとして、具体的な修正案を含むフィードバックを生成する。
        """
        if not self.prompt_manager:
            from src.models.audit import CriticFeedback
            return CriticFeedback(rewrite_guidance="Prompt manager not configured.")

        prompt = await self.prompt_manager.build_critic_feedback_prompt(
            issue_list=issue_list,
            draft_content=draft_content,
            blueprint=blueprint
        )

        # Handle both LLMService and raw generate_json function
        if hasattr(self.llm, "generate_json"):
            # Use await directly; AsyncMock will return return_value when awaited
            result = await self.llm.generate_json(purpose="critic", prompt=prompt)
        elif callable(self.llm):
            result = await self.llm(purpose="critic", prompt=prompt)
        else:
            from src.models.audit import CriticFeedback
            return CriticFeedback(rewrite_guidance="LLM client not configured.")

        from src.models.audit import CriticFeedback
        # Debugging: print result type
        # print(f"DEBUG: result type: {type(result)}, result: {result}")
        if hasattr(result, "metadata"):
            data = result.metadata
        elif isinstance(result, dict):
            data = result.get("metadata", result)
        else:
            data = result

        if isinstance(data, dict):
            return CriticFeedback.model_validate(data)

        return result if isinstance(result, CriticFeedback) else CriticFeedback(rewrite_guidance=str(result))

    async def validate_alibi_and_timeline(self, blueprint: str, script: str) -> Tuple[bool, List[str]]:
        """
        アリバイとタイムラインの整合性を検証する（スタブ）
        """
        return True, []

    async def audit_logical_consistency(self, book_id: int, ep_num: int, blueprint: str) -> Tuple[bool, str, float]:
        """作品のロジカル整合性をチェックします"""
        base_ok, base_feedback = await self._check_base_config(book_id, ep_num)
        if not base_ok:
            return False, base_feedback, 0.0

        plot_ok, plot_feedback = await self._check_plot_integrity(book_id, ep_num)
        if not plot_ok:
            return False, plot_feedback, 0.0

        char_ok, char_feedback = await self._check_character_actions(book_id)
        if not char_ok:
            return False, char_feedback, 0.0

        theme_ok, theme_feedback = await self._check_theme_continuity(blueprint)
        if not theme_ok:
            return False, theme_feedback, 0.0

        return True, "OK", 1.0

    async def _check_base_config(self, book_id: int, ep_num: int) -> Tuple[bool, str]:
        """基本設定の一貫性"""
        if self.repo is None:
            return True, "OK"
        settings = await self.repo.bible.get_plot(book_id, ep_num)
        if not settings:
            return False, "設定未設定"
        if not settings.get("scene_integrity", "false"):
            return False, "scene integrity violation"
        return True, "OK"

    async def _check_plot_integrity(self, book_id: int, ep_num: int) -> Tuple[bool, str]:
        """プロット全体の一貫性"""
        if self.repo is None:
            return True, "OK"
        plot = await self.repo.plot.get_plot(book_id, ep_num)
        if not plot:
            return False, "plot not found"
        if not await self._check_pacing(plot):
            return False, "inconsistent pacing"
        return True, "OK"

    async def _check_pacing(self, plot: PlotDbModel) -> bool:
        """テンションの一貫性チェック"""
        return True

    async def check_information_asymmetry(self, past_info: str, current_info: str) -> Tuple[bool, List[str]]:
        """
        情報の非対称性を検証する（スタブ）
        """
        return True, []

    async def _check_character_actions(self, book_id: int) -> Tuple[bool, str]:
        """キャラクターの行動一貫性（スタブ）"""
        return True, "OK"

    async def _check_theme_continuity(self, blueprint: str) -> Tuple[bool, str]:
        """テーマの連続性（スタブ）"""
        return True, "OK"

    async def analyze_tension_wave(self, book_id: int, ep_range: tuple = (1, 9999)) -> Any:
        """作品のtension履歴からNarrativeWavePatternを生成する"""
        try:
            from config.project_context import ProjectContext
            from src.models.audit import NarrativeWavePattern

            if self.repo is None:
                return NarrativeWavePattern()

            plots = await self.repo.plot.get_plots(book_id, ep_range[0], ep_range[1])
            if not plots:
                return NarrativeWavePattern()

            tension_history = [getattr(p, "tension", 50) for p in plots]

            if self.wave_analyzer is None:
                from src.backend.engine_narrative import WavePatternAnalyzer
                self.wave_analyzer = WavePatternAnalyzer(
                    threshold=ProjectContext.get_setting("catharsis_threshold", 65),
                    reset_value=ProjectContext.get_setting("catharsis_reset_value", 0),
                )

            return self.wave_analyzer.analyze(tension_history)
        except Exception as e:
            from src.models.audit import NarrativeWavePattern
            return NarrativeWavePattern(issues=[f"波パターン分析中にエラー: {str(e)}"])

    async def score_narrative_metrics(
        self,
        book_id: int,
        branch_id: int,
        ep_num: int,
        scene_num: int,
        scene_content: str,
        context: str = "",
        reporter: Any = None,
    ) -> List[Dict[str, Any]]:
        """1シーン分の没入スコアと物語メトリクスをLLMで算出する"""
        default_scores = [
            {"metric_name": "immersion_score", "score": 0.0, "reasoning": "スコアリング失敗時デフォルト"},
            {"metric_name": "pov_stability", "score": 0.0, "reasoning": ""},
            {"metric_name": "empathy_gap", "score": 1.0, "reasoning": ""},
            {"metric_name": "curiosity_hook_rate", "score": 0.0, "reasoning": ""},
            {"metric_name": "sensory_density", "score": 0.0, "reasoning": ""},
            {"metric_name": "catharsis_density", "score": 0.0, "reasoning": ""},
        ]
        if not scene_content or not scene_content.strip():
            return default_scores

        try:
            from src.models.audit import ImmersionScore

            prompt = (
                "以下の小説本文を、以下の6観点で0.0-1.0で評価してください。"
                "評価結果は JSON で返してください。\n"
                "{\n"
                '  "pov_stability": 0.0-1.0,\n'
                '  "empathy_gap": 0.0-1.0,\n'
                '  "curiosity_hook_rate": 0.0-1.0,\n'
                '  "sensory_density": 0.0-1.0,\n'
                '  "catharsis_density": 0.0-1.0\n'
                "}\n\n"
                "【本文】\n" + scene_content[:12000] + "\n"
            )
            if context:
                prompt += "\n【参考コンテキスト】\n" + context[:4000] + "\n"

            raw = await self.llm(purpose="narrative_metrics", prompt=prompt)
            data = raw.get("metadata", raw) if isinstance(raw, dict) else {}
            immersion = ImmersionScore(
                pov_stability=float(data.get("pov_stability", 0.0) or 0.0),
                empathy_gap=float(data.get("empathy_gap", 1.0) or 1.0),
                curiosity_hook_rate=float(data.get("curiosity_hook_rate", 0.0) or 0.0),
                sensory_density=float(data.get("sensory_density", 0.0) or 0.0),
            )
            total_score = immersion.calculate_total()
            scores = [
                {"metric_name": "immersion_score", "score": total_score, "reasoning": "加重合計"},
                {"metric_name": "pov_stability", "score": immersion.pov_stability, "reasoning": ""},
                {"metric_name": "empathy_gap", "score": immersion.empathy_gap, "reasoning": ""},
                {"metric_name": "curiosity_hook_rate", "score": immersion.curiosity_hook_rate, "reasoning": ""},
                {"metric_name": "sensory_density", "score": immersion.sensory_density, "reasoning": ""},
                {"metric_name": "catharsis_density", "score": float(data.get("catharsis_density", 0.0) or 0.0), "reasoning": ""},
            ]
            if reporter:
                reporter.report(f"ℹ️ Ep.{ep_num} Scene.{scene_num}: 没入スコア {total_score:.1f}", "info")
            return scores
        except Exception as e:
            if reporter:
                reporter.report(f"⚠️ スコアリング失敗: {type(e).__name__}: {e}", "warning")
            return default_scores
