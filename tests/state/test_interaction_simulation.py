from kernels.base import KernelState
from kernels.interaction_config import InteractionConfig
from kernels.interaction_manager import InteractionManager


def test_dramatic_arc_simulation():
    # ドラマチックな遷移を検証するための設定
    config = InteractionConfig(
        decay_rate=0.95,
        matrix={
            "resonance": {"resonance": 0.0, "hegemony": -0.4, "conflict": -0.1, "serenity": 0.1},
            "hegemony": {"resonance": -0.3, "hegemony": 0.0, "conflict": 0.1, "serenity": -0.1},
            "conflict": {"resonance": -0.1, "hegemony": 0.2, "conflict": 0.0, "serenity": -0.2},
            "serenity": {"resonance": 0.1, "hegemony": -0.1, "conflict": -0.2, "serenity": 0.0},
        }
    )
    manager = InteractionManager(config)

    # 初期状態: 氷の壁（高覇権、低共鳴）
    state = KernelState(resonance=10, hegemony=90, conflict=20, serenity=10)

    print("\n--- Simulation: The Collapse of the Ice Wall ---")
    print(f"T0: {state}")

    # 外部からの「共鳴へのアプローチ」をシミュレート
    resonance_impact = {"resonance": 15.0}

    for t in range(1, 11):
        state = manager.compute_next_state(state, resonance_impact, None)
        print(f"T{t}: {state}")

    # 検証: 最終的に覇権が低下し、共鳴が上昇しているか
    assert state.hegemony < 90
    assert state.resonance > 10

def test_conflict_escalation_simulation():
    config = InteractionConfig(
        decay_rate=0.9,
        matrix={
            "resonance": {"resonance": 0.0, "hegemony": -0.2, "conflict": -0.4, "serenity": 0.1},
            "hegemony": {"resonance": -0.1, "hegemony": 0.0, "conflict": 0.4, "serenity": -0.1},
            "conflict": {"resonance": -0.2, "hegemony": 0.3, "conflict": 0.0, "serenity": -0.5},
            "serenity": {"resonance": 0.1, "hegemony": -0.2, "conflict": -0.4, "serenity": 0.0},
        }
    )
    manager = InteractionManager(config)

    # 初期状態: 不安定な均衡
    state = KernelState(resonance=30, hegemony=50, conflict=30, serenity=30)

    # 外部からの「衝突の火種」を注入
    conflict_impact = {"conflict": 20.0}

    print("\n--- Simulation: Escalation of Conflict ---")
    print(f"T0: {state}")

    for t in range(1, 6):
        state = manager.compute_next_state(state, conflict_impact, None)
        print(f"T{t}: {state}")

    # 検証: 衝突(conflict)が上昇し、それに伴い覇権(hegemony)も刺激され上昇しているか
    assert state.conflict > 30
    assert state.hegemony > 50
