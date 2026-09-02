import pytest
from src.models.style_profile import StyleProfile, SentenceLengthModel, SentenceEndDistribution, MetaphorFrequency
from src.services.style_distiller import StyleDistillerService
from src.services.llm.mock_adapter import MockLLMAdapter


def test_style_profile_prompt_instruction():
    """StyleProfileから正しくプロンプト指示文が生成されるか検証"""
    profile = StyleProfile(
        id="test_style",
        name="テスト疾走調",
        tone_description="冷徹でシャープな語り口",
        sentence_length=SentenceLengthModel(avg=30, std_dev=8, min=10, max=60),
        sentence_end_distribution=SentenceEndDistribution(
            desu_masu=0.0, da_dearu=0.7, nominal=0.25, exclamatory=0.05, interrogative=0.0
        ),
        kerenmi_intensity=0.9,
        required_patterns=["体言止めで疾走感", "痛烈な比喩"],
        forbidden_patterns=["〜だったの連続"],
        few_shot_sample="男は剣を抜いた。銀光一閃。敵は地に伏した。",
    )

    prompt = profile.to_prompt_instruction()
    assert "■ 作家性DNA（文体バイアス）: 【テスト疾走調】" in prompt
    assert "冷徹でシャープな語り口" in prompt
    assert "平均30文字" in prompt
    assert "ケレン味・演出強度: 0.9/1.0" in prompt
    assert "体言止めで疾走感" in prompt
    assert "男は剣を抜いた。銀光一閃。" in prompt


@pytest.mark.asyncio
async def test_style_distiller_rule_based_fallback():
    """LLMが利用できない場合でもルールベースで妥当なStyleProfileが抽出されるか検証"""
    sample_text = """
    少年は闇の中で息を殺した。心臓の鼓動が耳元で鳴り響く。
    逃げ場はない。だが、諦める気も毛頭なかった。
    黒銀の魔剣が月光を浴びて妖しく輝く。
    「ここで終わりにするわけにはいかない」
    少年は覚悟を決めて駆け出した。
    """
    service = StyleDistillerService(llm_adapter=MockLLMAdapter())
    profile = await service.distill_from_text(sample_text, name_hint="ダーク疾走調")

    assert profile is not None
    assert profile.name == "ダーク疾走調"
    assert profile.sentence_length.avg > 0
    assert profile.kerenmi_intensity >= 0.7
    assert len(profile.few_shot_sample) > 0
