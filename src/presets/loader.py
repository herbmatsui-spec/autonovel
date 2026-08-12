"""
プリセットローダー
ジャンル名を受け取り、全プリセットファイルを読み込んで辞書として返却する。
"""

import json
import yaml
import os
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

PRESETS_BASE_DIR = Path(__file__).parent

# 対応ジャンル一覧
SUPPORTED_GENRES = [
    "zarma",
    "aku_reijo",
    "cheat_tensei",
    "slow_life",
    "dungeon_admin",
    "modern_cheat",
    "ts_tensei",
    "vrmmo",
    "loop"
]

# プリセットファイルマッピング
PRESET_FILES = {
    "bible": "bible/bible_preset_{genre}.j2",
    "tension": "tension/tension_curve_{genre}.yaml",
    "style": "style/style_dna_preset_{genre}.j2",
    "hooks": "hooks/hook_params_{genre}.json",
    "erotic": "erotic/erotic_rules_{genre}_kakuyomu.yaml",
    "characters": "characters/char_archetypes_{genre}.json",
    "titles": "titles/title_vars_{genre}.json",
    "marketing": "marketing/marketing_vars_{genre}.json"
}

# デフォルト値（ファイル不足時のフォールバック）
DEFAULT_VALUES = {
    "bible": "",
    "tension": {},
    "style": {},
    "hooks": {},
    "erotic": {},
    "characters": {},
    "titles": {},
    "marketing": {}
}


def load_j2_template(filepath: Path) -> str:
    """Jinja2テンプレートファイルを文字列として読み込み"""
    try:
        return filepath.read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.warning(f"Template file not found: {filepath}")
        return ""


def load_yaml(filepath: Path) -> Dict[str, Any]:
    """YAMLファイルを辞書として読み込み"""
    try:
        return yaml.safe_load(filepath.read_text(encoding="utf-8")) or {}
    except FileNotFoundError:
        logger.warning(f"YAML file not found: {filepath}")
        return {}
    except yaml.YAMLError as e:
        logger.error(f"YAML parse error in {filepath}: {e}")
        return {}


def load_json(filepath: Path) -> Dict[str, Any]:
    """JSONファイルを辞書として読み込み"""
    try:
        return json.loads(filepath.read_text(encoding="utf-8"))
    except FileNotFoundError:
        logger.warning(f"JSON file not found: {filepath}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error in {filepath}: {e}")
        return {}


def load_preset(genre: str) -> Dict[str, Any]:
    """
    指定ジャンルの全プリセットを読み込み、統合辞書として返却。
    
    Args:
        genre: ジャンル名（"zarma", "aku_reijo" 等）
        
    Returns:
        プリセット統合辞書。キー: bible, tension, style, hooks, erotic, characters, titles, marketing
        
    Raises:
        ValueError: 未対応ジャンルの場合
    """
    if genre not in SUPPORTED_GENRES:
        raise ValueError(f"Unsupported genre: {genre}. Supported: {SUPPORTED_GENRES}")
    
    preset = {}
    genre_dir = PRESETS_BASE_DIR / genre
    
    if not genre_dir.exists():
        logger.warning(f"Genre directory not found: {genre_dir}. Using defaults.")
        return {k: v for k, v in DEFAULT_VALUES.items()}
    
    # 各プリセットファイルを読み込み
    for key, rel_path in PRESET_FILES.items():
        filepath = genre_dir / rel_path.format(genre=genre)
        
        if rel_path.endswith(".j2"):
            preset[key] = load_j2_template(filepath)
        elif rel_path.endswith(".yaml"):
            preset[key] = load_yaml(filepath)
        elif rel_path.endswith(".json"):
            preset[key] = load_json(filepath)
        else:
            logger.warning(f"Unknown file type: {rel_path}")
            preset[key] = DEFAULT_VALUES.get(key, {})
    
    # メタデータ追加
    preset["_meta"] = {
        "genre": genre,
        "loaded_at": str(Path(__file__).stat().st_mtime),
        "files_loaded": list(preset.keys())
    }
    
    logger.info(f"Loaded preset for genre: {genre} (keys: {list(preset.keys())})")
    return preset


def get_preset_value(preset: Dict[str, Any], key: str, default: Any = None) -> Any:
    """プリセット辞書から安全に値を取得"""
    return preset.get(key, default)


def list_available_genres() -> list:
    """利用可能なジャンル一覧を返却"""
    return SUPPORTED_GENRES.copy()


def validate_preset(preset: Dict[str, Any]) -> Dict[str, Any]:
    """
    プリセットの完全性を検証し、不足キーを報告。
    
    Returns:
        {"valid": bool, "missing_keys": list, "warnings": list}
    """
    required_keys = set(PRESET_FILES.keys())
    loaded_keys = set(k for k in preset.keys() if not k.startswith("_"))
    missing_keys = required_keys - loaded_keys
    
    warnings = []
    for key in missing_keys:
        warnings.append(f"Missing preset key: {key}")
    
    # 重要ファイルの存在チェック
    critical_keys = ["bible", "tension", "style", "hooks"]
    for key in critical_keys:
        if key in preset and not preset[key]:
            warnings.append(f"Critical preset '{key}' is empty")
    
    return {
        "valid": len(missing_keys) == 0,
        "missing_keys": list(missing_keys),
        "warnings": warnings
    }


if __name__ == "__main__":
    # 簡易テスト
    import sys
    logging.basicConfig(level=logging.INFO)
    
    for genre in SUPPORTED_GENRES:
        try:
            preset = load_preset(genre)
            validation = validate_preset(preset)
            status = "OK" if validation["valid"] else "INCOMPLETE"
            print(f"[{status}] {genre}: keys={list(preset.keys())}, warnings={validation['warnings']}")
        except Exception as e:
            print(f"[ERROR] {genre}: {e}")
    
    sys.exit(0)