"""
tests/test_easy_mode_erotic.py
かんたんモードの官能設定および低過激度（1〜2）時のプロンプト生成テスト。
"""

import pytest
from src.models.planning_config import PlanningConfig
from src.engine.prompts.erotic_specialist import EroticSpecialist

def test_planning_config_erotic_params():
    """PlanningConfigがenable_eroticおよびerotic_intensityを正しく保持できることをテスト"""
    config = PlanningConfig(
        genre="ファンタジー",
        keywords="冒険, 魔法",
        style_key="style_web_standard",
        concept="最強の魔術師の物語",
        title="最強魔術師",
        enable_erotic=True,
        erotic_intensity=2
    )
    assert config.enable_erotic is True
    assert config.erotic_intensity == 2

def test_erotic_specialist_low_intensity_prompt():
    """過激度1〜2のときに、フェティシズム、心理的葛藤、焦らし表現の指針がプロンプトに含まれるかテスト"""
    specialist = EroticSpecialist()
    
    # 強度1のとき
    prompt_1 = specialist._build_layered_psychology_prompt(intensity=1)
    assert "低過激度（0〜2）での官能・焦らし表現の指針" in prompt_1
    assert "フェティシズム" in prompt_1
    assert "心理的葛藤" in prompt_1
    assert "シチュエーションによる焦らし" in prompt_1
    
    # 強度2のとき
    prompt_2 = specialist._build_layered_psychology_prompt(intensity=2)
    assert "低過激度（0〜2）での官能・焦らし表現の指針" in prompt_2
    
    # 強度3以上のとき（元の心理深層への誘導プロンプトになるか、あるいは空になるか）
    prompt_3 = specialist._build_layered_psychology_prompt(intensity=3)
    assert "低過激度（0〜2）での官能・焦らし表現の指針" not in prompt_3
