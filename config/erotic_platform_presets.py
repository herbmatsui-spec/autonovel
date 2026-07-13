"""
config/erotic_platform_presets.py
繝励Λ繝・ヨ繝輔か繝ｼ繝蛻･縲瑚｡ｨ迴ｾ縺ｮ蠑ｷ縺輔阪・繝ｪ繧ｻ繝・ヨ螳夂ｾｩ
"""
from typing import Any, Dict, List

PLATFORM_PRESETS: Dict[str, Dict[str, Any]] = {
    "kakuyomu_romance": {
        "name": "繧ｫ繧ｯ繝ｨ繝・域°諢帙き繝・ざ繝ｪ・・",
        "max_intensity": 2,
        "allowed_vocabulary_tier": "mild",
        "censorship_mode": "heavy",
        "description": "逶ｴ謗･逧・↑螳倩・謠丞・縺ｯ繧ｫ繝・ヨ縺励∫､ｺ蜚・↓縺ｨ縺ｩ繧√ｋ",
    },
    "nocturn_novel": {
        "name": "繝弱け繧ｿ繝ｼ繝ｳ繝弱・繝ｫ繧ｺ・・15逶ｸ蠖難ｼ・",
        "max_intensity": 3,
        "allowed_vocabulary_tier": "moderate",
        "censorship_mode": "partial",
        "description": "豈泌湊逧・↑螳倩・謠丞・繧定ｨｱ螳ｹ縲ら峩謗･蜷咲ｧｰ縺ｯ莨丞ｭ怜喧",
    },
    "adult_selfhost": {
        "name": "閾ｪ繧ｵ繧､繝・繝輔Ν陦ｨ迴ｾ",
        "max_intensity": 5,
        "allowed_vocabulary_tier": "intense",
        "censorship_mode": "none",
        "description": "陦ｨ迴ｾ縺ｮ蛻ｶ髯舌↑縺暦ｼ亥０い逅・ぎ繝ｼ繝峨Λ繧､繝ｳ縺ｮ縺ｿ驕ｩ逕ｨ・・",
    },
}

def get_preset(name: str) -> Dict[str, Any]:
    """繝励Μ繧ｻ繝・ヨ蜷阪°繧峨・繝ｪ繧ｻ繝・ヨ險ｭ螳壹ｒ蜿門ｾ励ょｭ伜惠縺励↑縺・ｴ蜷医・kakuyomu_romance繧定ｿ斐☆縲・"""
    return PLATFORM_PRESETS.get(name, PLATFORM_PRESETS["kakuyomu_romance"])

def get_preset_names() -> List[str]:
    """蛻ｩ逕ｨ蜿ｯ閭ｽ縺ｪ繝励Μ繧ｻ繝・ヨ蜷阪・繝ｪ繧ｹ繝医ｒ霑斐☆縲・"""
    return list(PLATFORM_PRESETS.keys())
