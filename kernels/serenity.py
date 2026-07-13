from typing import List

from kernels.base import KernelBase
from prompts.serenity_persona import SERENITY_PERSONA


class SerenityKernel(KernelBase):
    """
    低緊張状態を維持し、日常の深化と心理的聖域（Psychological Sanctuary）を設計するエンジン。
    物語に「水平方向の拡張（深化）」を与え、読者に精神的な休息と世界への愛着を提供することを目的とする。
    """

    def __init__(self, **kwargs):
        self.state_value = 0.0 # Interaction Matrix用
        super().__init__(**kwargs)
        self.persona = SERENITY_PERSONA

    async def execute(self, context):
        if await self.should_intervene(context):
            return await self.generate_serenity_scene(context)
        return None

    async def should_intervene(self, context) -> bool:
        """
        緊張度の低下後の安定期、または物語が過剰に加速し「休息」が必要なタイミングを検知する。
        物語の状態（Narrative State）に応じて、介入の閾値を動的に調整する。
        """
        analytics = getattr(context, 'analytics', None)
        if not analytics:
            return False

        # 物語状態の取得
        from kernels.graph import NarrativeState
        narrative_state = getattr(context, 'narrative_state', None)

        # 優先カーネルの確認
        priority_kernels = context.global_state.get('priority_kernels', [])
        is_priority = "serenity" in priority_kernels

        # 状態に応じた介入感度の調整
        # DAILY では積極的に日常を深化させ、CLIMAX では休息介入を抑制する
        sensitivity_multiplier = 1.0
        if narrative_state == NarrativeState.DAILY:
            sensitivity_multiplier = 1.4
        elif narrative_state == NarrativeState.CONFLICT:
            sensitivity_multiplier = 0.8
        elif narrative_state == NarrativeState.CLIMAX:
            sensitivity_multiplier = 0.4

        if is_priority:
            sensitivity_multiplier *= 1.5

        tension = getattr(analytics, 'tension', 0)
        tension_delta = getattr(analytics, 'tension_delta', 0)

        # 1. 激しい衝突の後の「凪」の状態 (Tensionが急落し、低水準で安定している)
        # 優先カーネルである場合は、より広い範囲で「休息が必要」と判断する
        base_thresh = 30 if not is_priority else 45
        if tension < (base_thresh * sensitivity_multiplier) and tension_delta <= 0:
            return True

        # 2. 物語の加速しすぎ防止 (Pacingが速すぎて、読者が情緒的な整理をする時間がない場合)
        if getattr(analytics, 'is_too_fast', False):
            return True

        # 3. 明示的な「休息/日常シーン」の要求がある場合
        if getattr(context, 'request_serenity', False):
            return True

        return False

    async def generate_serenity_scene(self, context):
        """
        日常の微小イベント（Micro-Event）を設計し、精神的な調和を演出する。
        """
        # 1. 静謐レベルの判定
        level = self._calculate_serenity_level(context)

        # 2. 静謐パターンの選択 ( config/data/serenity_patterns.json )
        pattern = self._select_serenity_pattern(level)

        # 3. 静謐シーンの生成 ( prompts/serenity_resonance_prompt.j2 )
        # scene = await self.llm.generate(
        #     prompt="prompts/serenity_resonance_prompt.j2",
        #     context=context,
        #     serenity_level=level,
        #     pattern=pattern
        # )

        # 4. 描写の深化研磨 ( prompts/serenity_polish_prompt.j2 )
        # polished_scene = await self.llm.generate(
        #     prompt="prompts/serenity_polish_prompt.j2",
        #     context=context,
        #     scene=scene
        # )

        # 5. 静謐品質監査 ( prompts/serenity_audit_prompt.j2 )
        # final_scene = await self._run_serenity_audit(polished_scene, context)

        # return final_scene
        return None

    def _select_serenity_pattern(self, level: int) -> dict:
        import json
        try:
            with open("config/data/serenity_patterns.json", "r", encoding="utf-8") as f:
                patterns = json.load(f)
            # レベルに合致するパターンを抽出
            matching = [p for p in patterns if p.get("serenity_level") == level]
            return matching[0] if matching else patterns[0]
        except Exception:
            return {"pattern_id": "default", "name": "General Serenity"}

    async def _run_serenity_audit(self, scene: str, context, max_retries: int = 2):
        """
        「単なる退屈」ではなく「質の高い静謐」であるかを監査する。
        """
        for i in range(max_retries):
            # audit_result = await self.llm.generate(
            #     prompt="prompts/serenity_audit_prompt.j2",
            #     context=context,
            #     scene=scene
            # )
            # if "PASS" in audit_result: return scene
            # scene = await self.llm.generate(
            #     prompt="修正指示に基づく再構成",
            #     context=context,
            #     audit=audit_result
            # )
            pass
        return scene

    def _calculate_serenity_level(self, context) -> int:
        """
        現在の心理状態と物語の文脈から、静謐の深度（Level 1-5）を決定する。
        """
        # 信頼度、親密度、および直前の緊張度から算出
        return 2 # デフォルト値

    def _get_sensory_anchors(self, level: int) -> List[str]:
        """
        レベルに応じた「ソフトな感覚的アンカー」を抽出する。
        """
        # 例: Level 1 -> "温かいお茶", "遠くの鳥の声"
        # Level 4 -> "完全な静寂", "同期した呼吸"
        return []

