
import asyncio
from unittest.mock import MagicMock

from kernels.base import KernelContext
from kernels.connection import ConnectionState
from kernels.graph import NarrativeState, NarrativeStateGraph, NarrativeStateManager
from kernels.pipeline import ConnectionPipeline


async def test_narrative_logic():
    print("=== Narrative State Logic End-to-End Test ===")

    # 1. Setup
    graph = NarrativeStateGraph()
    # 簡易的な遷移定義 (config相当)
    graph.add_node(NarrativeStateNode(NarrativeState.DAILY, "日常", "日常描写", [], "穏やか", ["いきなりの結末"]))
    graph.add_node(NarrativeStateNode(NarrativeState.INCIDENT, "事件", "転機", ["日常の確立"], "衝撃", ["即座の解決"]))
    graph.add_node(NarrativeStateNode(NarrativeState.CONFLICT, "葛藤", "深化", ["事件発生"], "緊張", ["唐突な和解"]))
    graph.add_node(NarrativeStateNode(NarrativeState.CLIMAX, "絶頂", "決着", ["葛藤の蓄積"], "激昂", ["都合の良い救済"]))
    graph.add_node(NarrativeStateNode(NarrativeState.RESOLUTION, "解決", "後日談", ["完了"], "安堵", []))

    graph.add_transition(NarrativeState.DAILY, NarrativeState.INCIDENT, path="standard")
    graph.add_transition(NarrativeState.INCIDENT, NarrativeState.CONFLICT, path="standard")
    graph.add_transition(NarrativeState.INCIDENT, NarrativeState.CLIMAX, path="twist") # Twist path
    graph.add_transition(NarrativeState.CONFLICT, NarrativeState.CLIMAX, path="standard")
    graph.add_transition(NarrativeState.CLIMAX, NarrativeState.RESOLUTION, path="standard")

    mgr = NarrativeStateManager(graph)

    # Mock kernels for pipeline
    # Async methods should return a coroutine or a Future
    mock_dialogue = MagicMock()
    async def mock_dialogue_exec(*args, **kwargs): return MagicMock()
    mock_dialogue.execute = mock_dialogue_exec

    mock_memory = MagicMock()
    async def mock_memory_exec(*args, **kwargs): return None
    mock_memory.execute = mock_memory_exec

    mock_resonance = MagicMock()
    async def mock_resonance_exec(*args, **kwargs): return None
    mock_resonance.execute = mock_resonance_exec

    mock_persona = MagicMock()
    mock_persona.generate_guidelines.return_value = "Base Guidelines"

    pipeline = ConnectionPipeline(
        dialogue_kernel=mock_dialogue,
        memory_kernel=mock_memory,
        resonance_kernel=mock_resonance,
        persona=mock_persona,
        narrative_state_graph=graph
    )
    # pipeline.narrative_mgr をテストの mgr と同期させる
    # pipeline 内部で NarrativeStateManager が別途作成されるため、外部の mgr と同じインスタンスを使うように差し替える
    pipeline.narrative_mgr = mgr

    context = KernelContext(
        trace_id="test-trace-123",
        global_state={"narrative_progress": 0.0},
    )
    # KernelContextの定義に合わせて補完
    context.narrative_state = NarrativeState.DAILY
    context.narrative_node = graph.get_node(NarrativeState.DAILY)

    # --- Test 1: Normal Progression (Standard Path) ---
    print("\n[Test 1] Normal Progression")
    for i in range(3):
        # フィードバック処理で状態を更新
        await pipeline.process_scene_feedback(
            "CharA", "CharB", ConnectionState(affection=50, trust=50, tension=20),
            ["シーンの出来事"], {"affection": 1.0}, context
        )
        print(f"Scene {i+1}: Current State = {context.narrative_state.name}, Progress = {context.global_state['narrative_progress']:.1f}")

    # --- Test 2: Twist Path ---
    print("\n[Test 2] Twist Path Selection")
    mgr.force_state(NarrativeState.INCIDENT)
    context.narrative_state = NarrativeState.INCIDENT
    context.global_state['preferred_narrative_path'] = 'twist'

    await pipeline.process_scene_feedback(
        "CharA", "CharB", ConnectionState(affection=50, trust=50, tension=50),
        ["衝撃的な展開"], {"tension": 10.0}, context
    )
    print(f"After Twist trigger: Current State = {context.narrative_state.name} (Expected: CLIMAX)")

    # --- Test 3: Forbidden Elements & Repair ---
    print("\n[Test 3] Violation Detection")
    mgr.force_state(NarrativeState.DAILY)
    context.narrative_state = NarrativeState.DAILY

    # DAILY状態で「いきなりの結末」という禁止ワードを注入
    await pipeline.process_scene_feedback(
        "CharA", "CharB", ConnectionState(affection=50, trust=50, tension=20),
        ["いきなりの結末を迎えた"], {"affection": 0.0}, context
    )

    if context.global_state.get('narrative_repair_required'):
        print("SUCCESS: Violation detected and repair triggered!")
    else:
        print("FAILURE: Violation NOT detected.")

    # --- Test 4: Narrative Inertia ---
    print("\n[Test 4] Narrative Inertia")
    mgr.force_state(NarrativeState.CLIMAX)
    context.narrative_state = NarrativeState.CLIMAX
    mgr.state_duration = 0 # Reset duration

    # CLIMAXではmin_duration=3。1回だけフィードバックしても遷移しないはず
    await pipeline.process_scene_feedback(
        "CharA", "CharB", ConnectionState(affection=50, trust=50, tension=90),
        ["決戦中"], {"tension": 1.0}, context
    )
    print(f"After 1 scene in CLIMAX: Current State = {context.narrative_state.name} (Expected: CLIMAX)")

if __name__ == "__main__":
    from kernels.graph import NarrativeStateNode  # Local import for script
    asyncio.run(test_narrative_logic())
