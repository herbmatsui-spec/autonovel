"""
config/platform_censorship_rules.py
プラットフォーム別の伏字変換ルール定義。
"""
from typing import Dict, List

PLATFORM_CENSORSHIP_RULES: Dict[str, List[Dict[str, str]]] = {
    "kakuyomu_romance": [
        {"src": "肌を重ねる", "dst": "肌を重ね◆◆"},
        {"src": "唇を重ねる", "dst": "唇を◆◆◆"},
        {"src": "腕の中に包む", "dst": "腕の中に◆◆"},
        {"src": "衣が滑り落ちる", "dst": "衣が◆◆◆◆◆"},
        {"src": "柔らかな丘", "dst": "◆◆◆◆丘"},
        {"src": "二人の夜", "dst": "二人の◆"},
    ],
    "nocturn_novel": [
        {"src": "セックス", "dst": "二人の夜"},
        {"src": "性行為", "dst": "親密な時間"},
        {"src": "裸", "dst": "衣を解いた姿"},
        {"src": "胸", "dst": "柔らかな起伏"},
        {"src": "キ・ス", "dst": "◆◆◇◆"},
        {"src": "抱く", "dst": "腕の中に包む"},
        {"src": "脱ぐ", "dst": "衣が滑り落ちる"},
    ],
    "adult_selfhost": [],
}


def get_censorship_rules(platform: str) -> List[Dict[str, str]]:
    """プラットフォーム別の伏字ルールリストを返す。"""
    return PLATFORM_CENSORSHIP_RULES.get(
        platform, PLATFORM_CENSORSHIP_RULES.get("kakuyomu_romance", [])
    )
