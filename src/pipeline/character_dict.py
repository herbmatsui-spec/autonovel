"""Character dictionary loader."""
from __future__ import annotations

import functools
from pathlib import Path
from typing import Optional

import yaml


@functools.lru_cache(maxsize=1)
def load_character_dict(path: Optional[str] = None) -> set[str]:
    """キャラクタ辞書を読み込み（シングルトン・キャッシュ付き）
    
    Args:
        path: YAML/JSONファイルパス。Noneの場合はデフォルト場所を探索
        
    Returns:
        キャラクター名のセット
    """
    if path is None:
        # デフォルト検索パス
        candidates = [
            Path(__file__).parent.parent.parent / "config" / "characters.yaml",
            Path(__file__).parent.parent.parent / "config" / "characters.yml",
            Path.cwd() / "config" / "characters.yaml",
        ]
        for candidate in candidates:
            if candidate.exists():
                path = str(candidate)
                break
        else:
            # 見つからない場合は空セット返却
            return set()
    
    path_obj = Path(path)
    if not path_obj.exists():
        return set()
    
    with open(path, "r", encoding="utf-8") as f:
        if path.endswith((".yaml", ".yml")):
            data = yaml.safe_load(f)
        elif path.endswith(".json"):
            import json
            data = json.load(f)
        else:
            raise ValueError(f"Unsupported format: {path}")
    
    # リスト形式を想定
    if isinstance(data, list):
        return set(data)
    elif isinstance(data, dict) and "characters" in data:
        return set(data["characters"])
    else:
        return set()


def save_character_dict(characters: set[str], path: str) -> None:
    """キャラクタ辞書を保存"""
    path_obj = Path(path)
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    
    data = {"characters": sorted(characters)}
    
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False)


__all__ = ["load_character_dict", "save_character_dict"]