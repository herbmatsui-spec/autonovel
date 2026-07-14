from kernels.base import KernelBase
from kernels.connection import ConnectionStagnationDetector, ConnectionState, TranslationEngine
from prompts.connection_persona import CONNECTION_PERSONA
from src.core.observability import get_structured_logger

logger = get_structured_logger("connection_kernel")
import json
import os
from typing import Any, Dict


class ConnectionKernel(KernelBase):
    """
    ConnectionKernel handles the structural implementation of relationship deepening,
    moving from simple intimacy to psychological resonance.
    """
    def __init__(self, engine):
        super().__init__("connection")
        self.engine = engine
        self.persona = CONNECTION_PERSONA
        self.stagnation_detector = ConnectionStagnationDetector()
        self.translator = TranslationEngine()

    async def execute(self, context):
        """
        Main execution logic for the Connection agent.
        Detects relationship stagnation and initiates resonance-building sequences.
        """
        # 1. Detect Stagnation/Need for Deepening
        history = getattr(context, 'connection_history', [])
        trigger = self.stagnation_detector.detect(history)

        if not trigger:
            # Even if not stagnant, we may want to maintain or subtly deepen resonance
            # based on plot markers.
            analytics = getattr(context, 'analytics', None)
            # 優先カーネルの確認
            priority_kernels = context.global_state.get('priority_kernels', [])
            is_priority = "connection" in priority_kernels

            if analytics is None:
                return None

            # 優先カーネルである場合は、is_connection_event が False でも介入を検討する
            if not getattr(analytics, 'is_connection_event', False) and not is_priority:
                logger.info("Relationship is evolving naturally. No intervention needed", kernel=self.persona['name'])
                return None

        logger.info("Trigger detected. Initiating Resonance Sequence",
                     kernel=self.persona['name'],
                     trigger_id=trigger.trigger_id if trigger else "natural")
        return await self.generate_resonance_event(context, trigger)

    async def generate_resonance_event(self, context, trigger=None):
        """
        Generates a scene designed to move characters from separate emotional orbits into a shared resonant state.
        Follows the pattern: Persona -> Trigger -> Pattern Library -> Polish -> Audit Loop.
        """
        from kernels.graph import NarrativeState
        from prompts.manager import PromptManager

        # Phase 27: 物語状態に基づく遷移トリガーの判定
        narrative_state = getattr(context, 'narrative_state', None)
        connection_state = getattr(context, 'connection_state', ConnectionState())

        # 関係性の深化（共鳴度や信頼度）が閾値を超えた場合、物語状態の遷移を促す
        # 例: DAILY 状態において共鳴度が 80 を超えた場合、INCIDENT（事件発生）への遷移を提案
        if narrative_state == NarrativeState.DAILY and connection_state.resonance > 80:
            logger.info(f"[Narrative Trigger] High resonance ({connection_state.resonance}) detected in DAILY state. Suggesting transition to INCIDENT.", kernel=self.persona['name'])
            context.global_state['suggested_narrative_transition'] = NarrativeState.INCIDENT.name

        # 1. Load Connection Patterns (Phase 5 will fully implement this library)
        pattern = self._select_connection_pattern(context, trigger)

        # 2. Prepare context
        narrative_summary = getattr(context, 'summary', "No summary available")
        target_chars = getattr(context, 'characters', ["Main Character"])
        connection_state = getattr(context, 'connection_state', ConnectionState())

        # Get current behavioral guidelines based on state
        guidelines = self.translator.get_all_guidelines(connection_state)

        prompt_vars = {
            "context": {"narrative_summary": narrative_summary},
            "target_characters": target_chars,
            "connection_state": connection_state.model_dump(),
            "behavioral_guidelines": guidelines,
            "selected_pattern": pattern,
            "trigger_reason": trigger.reason if trigger else "Natural progression of bond"
        }

        try:
            prompt_manager = PromptManager()
            # We'll need to create 'connection_resonance_prompt' in Phase 3
            prompt_text = await prompt_manager.render_async("connection_resonance_prompt", **prompt_vars)

            response = await self.engine.llm.generate(
                prompt=prompt_text,
                system_message=f"You are {self.persona['name']}: {self.persona['role']}. {self.persona['focus']}"
            )

            # 3. Polish (Phase 6: Resonance Polishing)
            polished_scene = await self.apply_resonance_polish(response)

            # 4. Audit Loop (Phase 8: Connection Audit)
            final_scene, final_impact = await self._run_connection_audit(polished_scene, response)

            return {
                "scene_proposal": final_scene,
                "analytics_update": final_impact,
                "applied_pattern": pattern.get('id', 'generic_resonance')
            }

        except Exception as e:
            logger.error("Error generating resonance event: %s", str(e), exc_info=True)
            return {"error": str(e)}

    def _select_connection_pattern(self, context, trigger) -> Dict[str, Any]:
        """
        Loads patterns from config/data/connection_patterns.json and selects the most appropriate one.
        """

        path = "config/data/connection_patterns.json"
        if not os.path.exists(path):
            return {"id": "generic", "name": "Generic Resonance", "description": "A subtle alignment of emotional states."}

        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                patterns = data.get("connection_patterns", [])

            if not patterns:
                return {"id": "generic", "name": "Generic Resonance", "description": "A subtle alignment of emotional states."}

            # Simple selection logic based on trigger or state
            # In a full implementation, this would be LLM-driven based on 'trigger_condition'
            if trigger and trigger.trigger_id == "RELATIONSHIP_STAGNATION":
                # Prioritize vulnerability reveal for stagnation
                return next((p for p in patterns if p['id'] == 'vulnerability_reveal'), patterns[0])

            # Default to the first pattern or a random one
            return patterns[0]
        except Exception as e:
            logger.error("Error loading connection patterns: %s", str(e), exc_info=True)
            return {"id": "generic", "name": "Generic Resonance", "description": "A subtle alignment of emotional states."}

    async def apply_resonance_polish(self, scene_text: str) -> str:
        """
        Refines the scene to emphasize micro-synchronicities and shared semiotics.
        """
        from prompts.manager import PromptManager
        try:
            prompt_manager = PromptManager()
            # We'll create 'resonance_polish_prompt' in Phase 6
            prompt_text = await prompt_manager.render_async("resonance_polish_prompt", scene=scene_text)

            return await self.engine.llm.generate(
                prompt=prompt_text,
                system_message=f"You are {self.persona['name']}: Specialist in Psychological Synchronization and Micro-synchronicities."
            )
        except Exception:
            return scene_text

    async def _run_connection_audit(self, scene: str, raw_response: str):
        """
        Audits for artificial acceleration or character breakage.
        """
        from prompts.manager import PromptManager
        prompt_manager = PromptManager()
        # We'll create 'connection_audit_prompt' in Phase 8
        audit_prompt = await prompt_manager.render_async("connection_audit_prompt", scene=scene)

        audit_res = await self.engine.llm.generate(
            prompt=audit_prompt,
            system_message="You are the Lead Relationship Auditor. Ensure the bond deepening is earned and not forced."
        )

        if "APPROVED" in audit_res:
            return scene, {"resonance_gain": 10, "trust_gain": 5}

        # Simplified: return raw for now or attempt one fix
        return scene, {"resonance_gain": 2, "trust_gain": 1}

