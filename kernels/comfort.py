from kernels.base import KernelBase
from prompts.comfort_persona import COMFORT_PERSONA
from src.core.observability import get_structured_logger
from typing import TYPE_CHECKING, Tuple

logger = get_structured_logger("comfort_kernel")

class ComfortKernel(KernelBase):
    """
    ComfortKernel handles the generation and refinement of scenes 
    dedicated to emotional relief, redemption, and catharsis.
    """
    def __init__(self, engine):
        super().__init__(engine)
        self.persona = COMFORT_PERSONA

    async def execute(self, context):
        """
        Main execution logic for the Comfort agent.
        Evaluates trigger conditions to determine if a cathartic intervention is needed.
        """
        if not await self.should_intervene(context):
            logger.info("No immediate need for cathartic intervention", kernel=self.persona['name'])
            return None

        logger.info("Trigger detected! Initiating cathartic resolution sequence", kernel=self.persona['name'])
        return await self.generate_comfort_scene(context)

    async def should_intervene(self, context) -> bool:
        """
        Analyzes PlotAnalytics to determine if the Comfort engine should take lead.
        """
        analytics = getattr(context, 'analytics', None)
        if not analytics:
            return False

        # 1. Explicit Request: If the plot explicitly marks this as a catharsis event
        if getattr(analytics, 'is_catharsis', False):
            return True

        # 2. High Tension Trigger: Tension is too high for too long (reader fatigue)
        tension = getattr(analytics, 'tension', 0)
        tension_delta = getattr(analytics, 'tension_delta', 0)
        if tension >= 80 and tension_delta >= 0:
            return True

        # 3. Resolution Gap: Tension dropped but catharsis is missing
        if tension < 40 and getattr(analytics, 'catharsis', 0) < 30:
            # If tension is low but no emotional payoff was delivered, Comfort should fill the gap
            return True

        return False

    async def generate_comfort_scene(self, context):
        """
        Generates a scene focused on relief and emotional resolution by selecting an optimal rescue pattern.
        """

        from prompts.manager import PromptManager

        # 1. Load Comfort Patterns
        patterns = self._load_comfort_patterns()

        # 2. Prepare context for the prompt
        narrative_summary = getattr(context, 'summary', "No summary available")
        target_chars = getattr(context, 'characters', ["Main Character"])
        analytics = getattr(context, 'analytics', None)

        # 3. Select the best pattern based on current state (Simple matching logic for now)
        # In a full implementation, this would use LLM to match the 'Lack' to the pattern's 'trigger_condition'
        selected_pattern = self._select_best_pattern(narrative_summary, analytics)

        prompt_vars = {
            "context": {"narrative_summary": narrative_summary},
            "target_characters": target_chars,
            "analytics": analytics if analytics else {"tension": 0, "tension_delta": 0, "emotional_state": "Unknown"},
            "selected_pattern": selected_pattern
        }

        # 4. Render prompt and call LLM
        try:
            prompt_manager = PromptManager()
            prompt_text = prompt_manager.render("comfort_reward_prompt", **prompt_vars)

            response = await self.engine.llm.generate(
                prompt=prompt_text,
                system_message=f"You are {self.persona['name']}: {self.persona['role']}. {self.persona['focus']}"
            )

            impact = self._parse_analytics_impact(response)

            # 4. Apply Afterglow Polish to deepen the resonance
            polished_scene = await self.apply_afterglow_polish(response)

            # 5. Audit Loop: Ensure the quality of the rescue
            final_scene, final_impact = await self._run_audit_loop(polished_scene, impact)

            logger.info("Pattern applied, polished, and audited",
                         kernel=self.persona['name'],
                         pattern_id=selected_pattern['id'],
                         impact=final_impact)

            return {
                "scene_proposal": final_scene,
                "raw_event": response,
                "analytics_update": final_impact,
                "applied_pattern": selected_pattern['id']
            }

        except Exception as e:
            logger.error("Error generating comfort scene", error=str(e), exc_info=True)
            return {"error": str(e)}

    def _load_comfort_patterns(self) -> list:
        """Loads rescue patterns from the config file."""
        path = "config/data/comfort_patterns.json"
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f).get("comfort_patterns", [])
        return []

    def _select_best_pattern(self, summary: str, analytics) -> dict:
        """
        Selects the most appropriate rescue pattern based on narrative context.
        Currently uses simple tension-based heuristics; will be upgraded to LLM-based 'Lack' matching.
        """
        patterns = self._load_comfort_patterns()
        if not patterns:
            return {"id": "generic", "name": "Generic Comfort", "approach": "General emotional relief"}

        tension = getattr(analytics, 'tension', 0)

        # High tension + physical threat -> physical_salvation
        if tension >= 80 and "danger" in summary.lower():
            return next((p for p in patterns if p['id'] == 'physical_salvation'), patterns[0])

        # Isolation/Loneliness -> fated_encounter
        if "alone" in summary.lower() or "lonely" in summary.lower():
            return next((p for p in patterns if p['id'] == 'fated_encounter'), patterns[0])

        # Default to validation or a random pattern
        return patterns[0]

    def _parse_analytics_impact(self, text: str) -> dict:
        """
        Extracts numerical impact values from the LLM response.
        """
        import re
        impacts = {}
        patterns = {
            "catharsis": r"catharsis:\s*(\d+)",
            "qol_delta": r"qol_delta:\s*(-?\d+)",
            "veneration_gain": r"veneration_gain:\s*([\d.]+)",
            "tension_new": r"tension_new:\s*(\d+)"
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, text)
            if match:
                val = match.group(1)
                impacts[key] = float(val) if '.' in val else int(val)

        return impacts

    async def _run_audit_loop(self, scene: str, impact: dict, max_retries: int = 2):
        """
        Audits the scene and iterates if it fails the quality checks.
        """
        from prompts.manager import PromptManager

        current_scene = scene
        current_impact = impact

        for attempt in range(max_retries):
            prompt_manager = PromptManager()
            audit_prompt = prompt_manager.render("comfort_audit_prompt", comfort_scene=current_scene)

            audit_response = await self.engine.llm.generate(
                prompt=audit_prompt,
                system_message="You are the Lead Narrative Auditor, specializing in Emotional Resonance and Catharsis."
            )

            if "APPROVED" in audit_response:
                logger.info("Audit passed", kernel=self.persona['name'], attempt=attempt + 1)
                return current_scene, current_impact

            logger.warning("Audit failed, attempting revision", kernel=self.persona['name'], attempt=attempt + 1, max_retries=max_retries)

            # Use the audit feedback to regenerate the scene
            revision_prompt = f"The previous version was rejected. Please revise it based on these instructions:\n\n{audit_response}\n\nOriginal Scene:\n{current_scene}"

            current_scene = await self.engine.llm.generate(
                prompt=revision_prompt,
                system_message=f"You are {self.persona['name']}: {self.persona['role']}. Focus on fixing the audit failures."
            )
            # Re-polish the revised scene
            current_scene = await self.apply_afterglow_polish(current_scene)
            # Update impact based on the new scene
            current_impact = self._parse_analytics_impact(current_scene)

        logger.error("Audit failed after maximum retries", kernel=self.persona['name'], max_retries=max_retries)
        return current_scene, current_impact

    async def apply_afterglow_polish(self, scene_text: str) -> str:
        """
        Refines the generated scene to deepen the emotional afterglow.
        """
        from prompts.manager import PromptManager
        try:
            prompt_manager = PromptManager()
            prompt_text = prompt_manager.render("afterglow_polish_prompt", cathartic_scene=scene_text)

            polished_text = await self.engine.llm.generate(
                prompt=prompt_text,
                system_message=f"You are {self.persona['name']}: Specialist in Afterglow and Emotional Resonance."
            )
            return polished_text
        except Exception as e:
            logger.error("Error applying afterglow polish", error=str(e), exc_info=True)
            return scene_text


# ==========================================
# 商用役割：全肯定キャラクター トリガー関数（ステップ14）
# ==========================================
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


# 全肯定セリフテンプレート
UNCONDITIONAL_SUPPORT_LINES = {
    # 基本肯定
    "trust": [
        "信じてる。あなたが就该这么做。",
        "あなたの判断を支持する。",
        "何があってもあなたの味方だ。",
    ],
    # 存在肯定
    "existence": [
        "あなたがいるだけで嬉しい。",
        " 그냥、あなたがいることが重要だ。",
        "有你在我身边就足够了。",
    ],
    # 能力肯定
    "ability": [
        "きみなら必ずできる。",
        "あなたの力は伟大だよ。",
        "きみを超える者はいない。",
    ],
    # 努力肯定
    "effort": [
        "それに尽くした时间是無駄じゃない。",
        "あなたの努力は伝わっている。",
        "今のリズムを维持して。",
    ],
    # 失敗時の肯定
    "failure_comfort": [
        "失敗してもいい。きみはもう十分に Женско。",
        "誰も完美じゃない。気にしない。",
        "跌倒了也别怕、私はここにいる。",
    ],
}


def unconditional_supporter_trigger(
    context,
    supporter_char: str,
    target_char: str,
    emotional_state: str,
    failure_detected: bool = False
) -> Tuple[str, float]:
    """全肯定キャラクターのトリガー条件をチェックし、適切なセリフを生成
    
    Args:
        context: 物語コンテキスト
        supporter_char: 全肯定キャラクター名
        target_char: 対象キャラクター名
        emotional_state: 対象キャラクターの感情状態
        failure_detected: 失敗イベントが発生したか
    
    Returns:
        (生成セリフ, 安心度スコア（0-100））
    """
    import random

    # 感情状態に応じたセリフ選択
    if failure_detected:
        line_pool = UNCONDITIONAL_SUPPORT_LINES["failure_comfort"]
        comfort_score = 85
    elif emotional_state in ("anxious", "worried", "sad"):
        line_pool = UNCONDITIONAL_SUPPORT_LINES["existence"] + UNCONDITIONAL_SUPPORT_LINES["trust"]
        comfort_score = 80
    elif emotional_state in ("stressed", "tired", "frustrated"):
        line_pool = UNCONDITIONAL_SUPPORT_LINES["effort"] + UNCONDITIONAL_SUPPORT_LINES["ability"]
        comfort_score = 75
    else:
        line_pool = UNCONDITIONAL_SUPPORT_LINES["trust"]
        comfort_score = 60

    selected_line = random.choice(line_pool)
    return (f"{supporter_char}は{target_char}に静かに微笑んだ。「{selected_line}」", comfort_score)


def should_trigger_unconditional_support(
    tension: float,
    protagonist_emotional_state: str,
    has_commercial_role_supporter: bool,
    recent_comfort_scene_ago: int = 999  # 前回のcomfort場面からの経過tick
) -> Tuple[bool, str]:
    """全肯定 поддержка トリガーをチェック
    
    Returns:
        (トリガーするか, トリガー理由)
    """
    if not has_commercial_role_supporter:
        return False, "全肯定役割のキャラクターが存在しない"

    # 高緊張後のリラックスポイント
    if tension > 75 and recent_comfort_scene_ago > 10:
        return True, "高緊張後のリラックスが必要"

    # 主人公が不安・失望状態
    if protagonist_emotional_state in ("anxious", "sad", "disappointed", "hopeless"):
        return True, "主人公の精神的サポートが必要"

    # 失敗後
    if recent_comfort_scene_ago > 20:
        return True, "安らぎの提供が長時間ない"

    return False, "トリガー条件未充足"

