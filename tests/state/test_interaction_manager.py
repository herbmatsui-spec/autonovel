from archive.kernels.base import KernelState
from archive.kernels.interaction_config import InteractionConfig
from archive.kernels.interaction_manager import InteractionManager


def test_interaction_matrix_calculation():
    # 簡易的な設定でテスト
    config = InteractionConfig(
        decay_rate=1.0,  # 減衰なし
        matrix={
            "resonance": {"resonance": 0.0, "hegemony": -0.5, "conflict": -0.2, "serenity": 0.1},
            "hegemony": {"resonance": -0.1, "hegemony": 0.0, "conflict": 0.2, "serenity": -0.1},
            "conflict": {"resonance": -0.2, "hegemony": 0.3, "conflict": 0.0, "serenity": -0.5},
            "serenity": {"resonance": 0.1, "hegemony": -0.2, "conflict": -0.3, "serenity": 0.0},
        },
    )
    manager = InteractionManager(config)

    # 初期状態: 覇権が非常に強く、他が低い
    initial_state = KernelState(resonance=10, hegemony=80, conflict=10, serenity=10)

    # 外部影響なしで更新
    external_impact = {}
    next_state = manager.compute_next_state(initial_state, external_impact, None)

    # 覇権(80)が共鳴(resonance)に-0.5の影響を与えるため、共鳴は低下するはず
    # 10 + (80 * -0.5) = -30 -> クランプされて 0
    assert next_state.resonance == 0

    # 覇権(80)が葛藤(conflict)に0.3の影響を与えるため、葛藤は上昇するはず
    # 減衰項(10*1.0) + 共鳴への影響(10*-0.2) + 覇権への影響(80*0.3) + 自分への影響(10*0.0) + セレニティへの影響(10*-0.5) 
    # = 10 -2 + 24 + 0 -5 = 27
    assert next_state.conflict == 27


def test_state_clamping():
    config = InteractionConfig(
        decay_rate=1.0,
        matrix={
            k: {ik: 10.0 for ik in ["resonance", "hegemony", "conflict", "serenity"]}
            for k in ["resonance", "hegemony", "conflict", "serenity"]
        },
    )
    manager = InteractionManager(config)
    initial_state = KernelState(resonance=90, hegemony=90, conflict=90, serenity=90)

    external_impact = {}
    next_state = manager.compute_next_state(initial_state, external_impact, None)

    # 全ての値を100にクランプ
    assert next_state.resonance == 100
    assert next_state.hegemony == 100
    assert next_state.conflict == 100
    assert next_state.serenity == 100


def test_decay_logic():
    config = InteractionConfig(
        decay_rate=0.5,  # 強い減衰
        matrix={
            k: {ik: 0.0 for ik in ["resonance", "hegemony", "conflict", "serenity"]}
            for k in ["resonance", "hegemony", "conflict", "serenity"]
        },
    )
    manager = InteractionManager(config)
    initial_state = KernelState(resonance=100, hegemony=100, conflict=100, serenity=100)

    external_impact = {}
    next_state = manager.compute_next_state(initial_state, external_impact, None)

    # 100 * 0.5 = 50
    assert next_state.resonance == 50
    assert next_state.hegemony == 50
    assert next_state.conflict == 50
    assert next_state.serenity == 50
