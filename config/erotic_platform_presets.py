import base64
from typing import Any, Dict, List

def _b(s: str) -> str:
    return base64.b64decode(s).decode("utf-8")

PLATFORM_PRESETS: Dict[str, Dict[str, Any]] = {
    "kakuyomu_romance": {
        "name": _b("44Kr44Kv44Oo44Og77yI5oGL5oSb44Kr44OG44K044Oq44O877yJ"),
        "max_intensity": 2,
        "allowed_vocabulary_tier": "mild",
        "censorship_mode": "heavy",
        "description": "直接的な官能描写はカットし、暗示にとどめる",
    },
    "nocturn_novel": {
        "name": _b("44OO44Kv44K/44O844Oz44OO44OZ44Or44K677yIUjE155u45b2T77yJ"),
        "max_intensity": 3,
        "allowed_vocabulary_tier": "moderate",
        "censorship_mode": "partial",
        "description": "比喩的な官能描写を許容。直接名称は伏字化",
    },
    "adult_selfhost": {
        "name": _b("6Ieq44K144Kk44OI44OV44Or6KGo54++77yIUjE477yJ"),
        "max_intensity": 5,
        "allowed_vocabulary_tier": "intense",
        "censorship_mode": "none",
        "description": "表現の制限なし（倫理ガイドラインのみ適用）",
    },
}

def get_preset(name: str) -> Dict[str, Any]:
    return PLATFORM_PRESETS.get(name, PLATFORM_PRESETS["kakuyomu_romance"])

def get_preset_names() -> List[str]:
    return list(PLATFORM_PRESETS.keys())
