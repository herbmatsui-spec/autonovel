from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from kernels.base import KernelContext
from kernels.connection import ConnectionState
from kernels.dialogue import DialogueConfig, DialogueKernel
from kernels.graph import NarrativeState, NarrativeStateGraph, NarrativeStateManager
from kernels.memory import MemoryKernel
from kernels.resonance import ResonanceKernel


class SceneConnectionContext(BaseModel):
    """
    あるシーンにおける、特定のペア間の完全な接続コンテキスト。
    """
    char_a: str
    char_b: str
    state: ConnectionState
    role: Optional[Any] # SocialRole
    current_tags: List[str]
    dialogue_config: DialogueConfig
    guidelines_prompt: str
    resonance_event_prompt: str

class ConnectionPipeline:
    """
    出来事 -> 感情変動 -> 描写指示 というフィードバックループを管理するパイプライン。
    """

    def __init__(
        self,
        dialogue_kernel: DialogueKernel,
        memory_kernel: MemoryKernel,
        resonance_kernel: ResonanceKernel,
        hegemony_kernel: Any = None,
        conflict_kernel: Any = None,
        serenity_kernel: Any = None,
        persona: Any = None, # ConnectionPersona
        narrative_state_graph: Optional[NarrativeStateGraph] = None
    ):
        self.dialogue_eng = dialogue_kernel
        self.memory_sys = memory_kernel
        self.resonance_eng = resonance_kernel
        self.hegemony_eng = hegemony_kernel
        self.conflict_eng = conflict_kernel
        self.serenity_eng = serenity_kernel
        self.persona = persona

        # 物語状態マネージャーの初期化
        if narrative_state_graph:
            self.narrative_mgr = NarrativeStateManager(narrative_state_graph)
        else:
            self.narrative_mgr = None

        from kernels.interaction_manager import InteractionManager
        from kernels.preset_triggers import create_preset_triggers
        self.interaction_mgr = InteractionManager()
        self.trigger_registry = create_preset_triggers()

    async def process_scene_feedback(self, char_a: str, char_b: str, state: ConnectionState,
                                     scene_events: List[str], emotional_shifts: Dict[str, float],
                                     context: KernelContext) -> ConnectionState:
        """
        シーン終了後のフィードバック処理。感情値を更新し、記憶に刻む。
        """
        # 1. 感情値の更新
        for dim, shift in emotional_shifts.items():
            if hasattr(state, dim):
                current_val = getattr(state, dim)
                setattr(state, dim, max(0.0, min(100.0, current_val + shift)))

        # --- Kernel Interaction Matrix (KIM) 処理 ---
        # 現在のカーネル状態を収集
        from kernels.base import KernelState
        current_k_state = KernelState(
            resonance=self.resonance_eng.state_value,
            hegemony=getattr(self.hegemony_eng, 'state_value', 0.0) if self.hegemony_eng else 0.0,
            conflict=getattr(self.conflict_eng, 'state_value', 0.0) if self.conflict_eng else 0.0,
            serenity=getattr(self.serenity_eng, 'state_value', 0.0) if self.serenity_eng else 0.0
        )
        # 感情変動を外部刺激として変換
        external_impact = {
            "resonance": emotional_shifts.get("affection", 0.0) * 0.5 + emotional_shifts.get("trust", 0.0) * 0.5,
            "hegemony": emotional_shifts.get("tension", 0.0) * 0.2,
            "conflict": emotional_shifts.get("tension", 0.0) * 0.5,
            "serenity": -emotional_shifts.get("tension", 0.0) * 0.3
        }

        # 次の状態を計算
        next_k_state = await self.interaction_mgr.compute_next_state(current_k_state, external_impact, context)

        # デバッグログの出力
        print(f"[KIM Debug] {char_a} <-> {char_b} state transition:")
        print(f"  Prev: {current_k_state}")
        print(f"  Impact: {external_impact}")
        print(f"  Next: {next_k_state}")

        # 各カーネルに状態をフィードバック
        self.resonance_eng.state_value = next_k_state.resonance
        if self.hegemony_eng: self.hegemony_eng.state_value = next_k_state.hegemony
        if self.conflict_eng: self.conflict_eng.state_value = next_k_state.conflict
        if self.serenity_eng: self.serenity_eng.state_value = next_k_state.serenity

        # --- Trigger Check ---
        activated_triggers = self.trigger_registry.check_triggers(current_k_state, next_k_state)
        for trigger in activated_triggers:
            await trigger.action(context, self)
        # --------------------------------------------

        # --- Narrative State Injection & Update ---
        if self.narrative_mgr:
            context.narrative_state = self.narrative_mgr.current_state
            context.narrative_node = self.narrative_mgr.get_current_node()
            # 物語状態に基づくベースライン緊張度と描写密度を注入
            context.global_state['base_tension'] = self.narrative_mgr.current_base_tension
            context.global_state['description_density'] = self.narrative_mgr.current_description_density

            # Phase 12: プロット生成後の状態更新（簡易実装）
            # 進捗率（例: 現在のエピソード/総エピソード数）に基づいて次状態を提案し、遷移させる
            # 注: 実際の進捗率は context.global_state 等から取得すべきだが、ここでは簡易的に 0.1 刻みで進める例とする
            current_progress = context.global_state.get('narrative_progress', 0.0)

            # デバッグ用: forced_state が global_state にある場合はそれを優先的に使用
            forced_state_name = context.global_state.get('forced_narrative_state')
            forced_state = None
            if forced_state_name:
                try:
                    forced_state = NarrativeState[forced_state_name]
                except KeyError:
                    print(f"Warning: Invalid forced state name {forced_state_name}")

            # 物語の方向性（例: twist_mode）をglobal_stateから取得
            preferred_path = context.global_state.get('preferred_narrative_path', 'standard')
            next_state = self.narrative_mgr.suggest_next_state(
                current_progress + 0.1,
                forced_state=forced_state,
                preferred_path=preferred_path
            )

            if next_state != self.narrative_mgr.current_state:
                print(f"[Narrative] Transitioning state: {self.narrative_mgr.current_state} -> {next_state}")
                self.narrative_mgr.transition_to(next_state)
                context.narrative_state = next_state
                context.narrative_node = self.narrative_mgr.get_current_node()

            context.global_state['narrative_progress'] = current_progress + 0.1
            # 強制遷移後はフラグをクリアして通常フローに戻す
            if forced_state_name:
                context.global_state['forced_narrative_state'] = None

            # Phase 20: 状態違反の一次検出 (キーワードベース)
            # シーンイベントの中に、あるいは現在のコンテキストから禁止事項の違反をチェック
            violations = self.narrative_mgr.check_current_violations(" ".join(scene_events))
            if violations:
                print(f"[Narrative Warning] State {self.narrative_mgr.current_state} violations detected: {violations}")
                context.global_state['narrative_violations'] = violations
                # Phase 23: 自動再生成トリガーの設定
                context.global_state['narrative_repair_required'] = True
                context.global_state['narrative_repair_count'] = context.global_state.get('narrative_repair_count', 0) + 1
            else:
                context.global_state['narrative_violations'] = []
                context.global_state['narrative_repair_required'] = False
                context.global_state['narrative_repair_count'] = 0

        # 2. 重要イベントの記憶化 (変動が激しい場合に自動的にマイルストーン化)
        # 閾値は本来設定から取得すべきだが、ここでは暫定的に10.0を使用。
        # 将来的に GlobalConfigModel に memory_event_threshold 等を追加して参照させる。
        if any(abs(shift) >= 10.0 for shift in emotional_shifts.values()):
            event_desc = " / ".join(scene_events) if scene_events else "名もなき感情の揺れ"
            # タグの抽出（簡易的にイベント文から抽出する想定）
            tags = [tag for tag in scene_events if len(tag) < 10]
            await self.memory_sys.execute({
                "action": "add",
                "char_a": char_a,
                "char_b": char_b,
                "event": event_desc,
                "impact": emotional_shifts,
                "tags": tags
            }, context)

        return state

    async def inject_resonance_event(self, event: Any, context: KernelContext):
        """
        トリガーによって強制的に共鳴イベントを注入する。
        """
        context.global_state['forced_resonance_event'] = event
        print(f"[Pipeline] Forced Resonance Event Injected: {event.event_type}")

    def _get_priority_kernels(self, state: NarrativeState) -> List[str]:
        """物語の状態に基づいて優先的に適用すべきカーネルを決定する"""
        mapping = {
            NarrativeState.DAILY: ["serenity", "connection"],
            NarrativeState.INCIDENT: ["connection", "hegemony"],
            NarrativeState.CONFLICT: ["hegemony", "conflict"],
            NarrativeState.PRE_CLIMAX: ["conflict", "hegemony"],
            NarrativeState.CLIMAX: ["hegemony", "conflict"],
            NarrativeState.RESOLUTION: ["serenity", "connection"],
        }
        return mapping.get(state, ["connection"])

    async def prepare_next_scene_context(self, char_a: str, char_b: str, state: ConnectionState,
                                      role: Optional[Any], current_tags: List[str],
                                      context: KernelContext) -> SceneConnectionContext:
        """
        次のシーンに必要な全ての接続コンテキストを生成する。
        """
        # 0. 物語状態に基づく優先カーネルの決定
        if self.narrative_mgr:
            priority_kernels = self._get_priority_kernels(self.narrative_mgr.current_state)
            context.global_state['priority_kernels'] = priority_kernels
            print(f"[Pipeline] Priority Kernels for {self.narrative_mgr.current_state}: {priority_kernels}")

        # 1. ダイアログ設定の決定
        diag_config = await self.dialogue_eng.execute(state, context)
        diag_str = self.dialogue_eng.generate_dialogue_instruction(char_a, char_b, diag_config)

        # 2. 統合的な描写ガイドラインの生成
        guidelines = self.persona.generate_guidelines(
            char_a, char_b, state,
            dialogue_config_str=diag_str,
            role=role,
            current_tags=current_tags
        )

        # Phase 30 & 33: 物語状態に基づく動的ガイドラインの注入
        if self.narrative_mgr:
            node = self.narrative_mgr.get_current_node()
            state_name = self.narrative_mgr.current_state.name

            # 1. 状態固有の推奨トーンと説明の注入
            if node:
                guidelines += f"\n\n[現在の物語状態: {node.name}]\n"
                guidelines += f"方向性: {node.description}\n"
                guidelines += f"推奨トーン: {node.recommended_tone}"

            # 2. 描写密度の動的反映
            density = self.narrative_mgr.current_description_density
            density_instructions = {
                "High": "情景描写、心理描写、五感を詳細に描き込み、シーンの空気感を濃厚に表現してください。",
                "Medium-High": "重要なポイントに重点的に詳細な描写を加え、シーンの奥行きを出してください。",
                "Medium": "標準的な描写密度で、物語の進行と描写のバランスを維持してください。",
                "Medium-Low": "描写を簡潔にし、テンポを上げて展開の速度感を重視してください。",
                "Low": "描写を最小限に抑え、アクションやダイアログを中心とした極めて速いテンポで描写してください。"
            }
            density_text = density_instructions.get(density, density_instructions["Medium"])
            guidelines += f"\n\n[描写密度設定: {density}]\n{density_text}"

        # Phase 23: 状態違反がある場合の修正指示の注入
        if context.global_state.get('narrative_repair_required'):
            violations = context.global_state.get('narrative_violations', [])
            current_state = context.narrative_state

            # 修正プロンプトの生成（ここでは簡易的に文字列として注入）
            # 本来は PromptManager を通じて render されるべきだが、パイプラインでの即時適用のためガイドラインに追加する
            repair_instruction = (
                f"\n\n[🚨 物語構造修正指示]\n"
                f"現在の状態 {current_state} において、以下の禁止事項への抵触が検出されました:\n"
                f"{', '.join(violations)}\n"
                f"これらの違反を解消し、{current_state} にふさわしい展開に修正してください。"
            )
            guidelines += repair_instruction

        # 3. 共鳴イベントのチェック
        res_event = await self.resonance_eng.execute(state, context)
        res_prompt = self.resonance_eng.generate_plot_injection_prompt(char_a, char_b, res_event) if res_event else ""

        return SceneConnectionContext(
            char_a=char_a,
            char_b=char_b,
            state=state,
            role=role,
            current_tags=current_tags,
            dialogue_config=diag_config,
            guidelines_prompt=guidelines,
            resonance_event_prompt=res_prompt
        )

