from kernels.base import KernelState
from kernels.interaction_config import InteractionConfig
from kernels.interaction_manager import InteractionManager


def test_interaction_matrix_calculation():
    # 簡易的な設定でテスト
    config = InteractionConfig(
        decay_rate=1.0, # 減衰なし
        matrix={
            "resonance": {"resonance": 0.0, "hegemony": -0.5, "conflict": -0.2, "serenity": 0.1},
            "hegemony": {"resonance": -0.1, "hegemony": 0.0, "conflict": 0.2, "serenity": -0.1},
            "conflict": {"resonance": -0.2, "hegemony": 0.3, "conflict": 0.0, "serenity": -0.5},
            "serenity": {"resonance": 0.1, "hegemony": -0.2, "conflict": -0.3, "serenity": 0.0},
        }
    )
    manager = InteractionManager(config)

    # 初期状態: 覇権が非常に強く、他が低い
    initial_state = KernelState(resonance=10, hegemony=80, conflict=10, serenity=10)

    # 外部影響なしで更新
    next_state = manager.compute_next_state(initial_state, None, None)

    # 覇権(80)が共鳴(resonance)に-0.5の影響を与えるため、共鳴は低下するはず
    # 10 + (80 * -0.5) = -30 -> クランプされて 0
    assert next_state.resonance == 0

    # 覇権(80)が葛藤(conflict)に0.2の影響を与えるため、葛藤は上昇するはず
    # 10 + (80 * 0.2) = 26
    assert next_state.conflict == 26

def test_state_clamping():
    config = InteractionConfig(
        decay_rate=1.0,
        matrix={k: {ik: 10.0 for ik in ["resonance", "hegemony", "conflict", "serenity"]} for k in ["resonance", "hegemony", "conflict", "serenity"]}
    )
    manager = InteractionManager(config)
    initial_state = KernelState(resonance=90, hegemony=90, conflict=90, serenity=90)

    next_state = manager.compute_next_state(initial_state, None, None)

    # 全ての値を100にクランプ
    assert next_state.resonance == 100
    assert next_state.hegemony == 100
    assert next_state.conflict == 100
    assert next_state.serenity == 100

def test_decay_logic():
    config = InteractionConfig(
        decay_rate=0.5, # 強い減衰
        matrix={k: {ik: 0.0 for ik in ["resonance", "hegemony", "conflict", "serenity"]} for k in ["resonance", "hegemony", "conflict", "serenity"]}
    )
    manager = InteractionManager(config)
    initial_state = KernelState(resonance=100, hegemony=100, conflict=100, serenity=100)

    next_state = manager.compute_next_state(initial_state, None, None)

    # 100 * 0.5 = 50
    assert next_state.resonance == 50
    assert next_state.hegemony == 50
    assert next_state.conflict == 50
    assert next_state.serenity == 50
