"""
formatters/erotic_censor.py
プラットフォーム別の伏字（shading）変換フォーマッター。
リファクタリング済み: 固定dict → config/platform_censorship_rules.py 参照
"""
from typing import Dict

from config.erotic_platform_presets import get_preset
from config.platform_censorship_rules import get_censorship_rules


def apply_censorship(text: str, preset_name: str = "kakuyomu_romance") -> str:
    """
    プリセットに基づいて伏字変換を適用する。

    変換ルールは config/platform_censorship_rules.py で管理される。
    """
    preset = get_preset(preset_name)
    mode = preset.get("censorship_mode", "heavy")

    if mode == "none":
        return text

    rules = get_censorship_rules(preset_name)
    result = text
    for rule in rules:
        src = rule["src"]
        dst = rule["dst"]
        result = result.replace(src, dst)

    return result


def generate_censored_filename(original: str) -> str:
    """元ファイル名から伏字版ファイル名を生成する。"""
    if original.endswith(".txt"):
        return original.replace(".txt", "_censored.txt")
    return f"{original}_censored"


# 後方互換性: 旧 CENSORSHIP_TABLE は廃止済み
# 旧テーブルユーザーは get_censorship_rules("kakuyomu_romance") に移行すること
CENSORSHIP_TABLE: Dict[str, str] = {}
