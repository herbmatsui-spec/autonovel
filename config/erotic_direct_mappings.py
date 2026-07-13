"""
配置/官能直接映射.py
直接表現→比喗表現的映射定义。
可以通过编辑此文件添加新词汇。
"""

from typing import Final

DIRECT_TO_METAPHOR: Final[dict[str, str]] = {
    # 核心映射（必需）
    "セックス": "二人の夜",
    "抱く": "肌を重ねる",
    "キス": "唇を重ねる",
    "裸": "衣を解く",
    "胸": "柔らかな起伏",
    "脱ぐ": "衣が滑り落ちる",
    # 新規5対
    "腰": "穏やかな律動",
    "唇": "吐息の温もり",
    "吐息": "乱れる呼吸",
    "股間": "身体の中心",
    "濡れる": "湿润する",
}

# 強度≤2时的额外抽象化
EXTRA_ABSTRACTIONS: Final[dict[str, str]] = {
    "愛する": "温もりを確かめ合う",
    "肌を重ねる": "二人の夜を過ごす",
    # 新規5対
    "陶酔": "波の収束",
    "欲望": "燃える糸",
    "背徳": "闇の底",
    "熱": "熱量の伝播",
    "感情": "沈静の波",
}

def get_combined_mappings():
    """
    Combine all metaphor mappings into a single dictionary.
    """
    combined = DIRECT_TO_METAPHOR.copy()
    combined.update(EXTRA_ABSTRACTIONS)
    return combined

__all__ = ["DIRECT_TO_METAPHOR", "EXTRA_ABSTRACTIONS", "get_combined_mappings"]
