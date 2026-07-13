
import pytest

from src.agents.audit import InternalLogicValidator
from src.models.plot import MysteryEpisode


@pytest.mark.asyncio
async def test_enigma_red_herring_and_catharsis():
    """
    フェーズ6,7: Red Herring管理とカタルシス計算のテスト
    """
    ep = MysteryEpisode()

    # Red Herringの追加
    rh_id = ep.enigma.add_red_herring("現場に残された血文字", 1)
    assert len(ep.enigma.red_herrings) == 1
    assert ep.enigma.red_herrings[0].id == rh_id
    assert ep.enigma.red_herrings[0].clue == "現場に残された血文字"

    # カタルシスフラグを立てる
    ep.analytics.is_catharsis = True
    ep.enigma.knowledge_delta = 0.8  # 高い驚き
    ep.enigma.truth_convergence = 0.9 # 高い納得感
    ep.enigma.unfairness_score = 0.0  # フェア

    # Red Herringを排除せずに計算
    score1 = ep.calculate_mystery_catharsis()
    assert score1 == int((0.8 * 0.9) * 100) # 72

    # Red Herringを排除してから再計算 (ボーナスが付与される)
    ep.enigma.eliminate_red_herring(rh_id, 2, "血ではなくケチャップだった")
    score2 = ep.calculate_mystery_catharsis()
    assert score2 > score1

@pytest.mark.asyncio
async def test_internal_logic_validator_stubs():
    """
    フェーズ3,4,5: Audit機能の実行テスト (スタブとして例外を出さずに返るか)
    """
    class DummyPromptManager:
        pass

    class DummyLLM:
        async def generate_json(self, *args, **kwargs):
            class Res:
                success = True
                metadata = {"is_consistent": True, "is_fair": True, "is_optimal": True}
            return Res()

    validator = InternalLogicValidator(pm=DummyPromptManager(), generate_json=DummyLLM().generate_json)

    # Phase 3
    is_ok, errs = await validator.validate_alibi_and_timeline("blueprint", "script")
    assert is_ok is True
    assert errs == []

    # Phase 4
    is_fair, unfair_elems = await validator.check_information_asymmetry("past", "current")
    assert is_fair is True
    assert unfair_elems == []
