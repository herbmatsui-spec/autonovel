"""Tests for character dictionary loader."""
from __future__ import annotations

import pytest
import tempfile
import yaml
from pathlib import Path

from src.pipeline.character_dict import load_character_dict, save_character_dict


class TestCharacterDict:
    """キャラ辞書ローダーテスト"""

    def test_load_yaml(self):
        """YAML読み込みテスト"""
        chars = load_character_dict("config/characters.yaml")
        assert isinstance(chars, set)
        assert "A" in chars
        assert "B" in chars
        assert "主人公" in chars

    def test_load_nonexistent_returns_empty(self):
        """存在しないファイル指定で空セット返却"""
        chars = load_character_dict("/nonexistent/path.yaml")
        assert chars == set()

    def test_save_and_load_roundtrip(self):
        """保存→読み込みラウンドトリップ"""
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            temp_path = f.name
        
        try:
            original = {"A", "B", "C", "テストキャラ"}
            save_character_dict(original, temp_path)
            
            loaded = load_character_dict(temp_path)
            assert loaded == original
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_save_creates_directory(self):
        """保存時にディレクトリ作成"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "subdir" / "chars.yaml"
            save_character_dict({"X", "Y"}, str(path))
            assert path.exists()
            
            loaded = load_character_dict(str(path))
            assert loaded == {"X", "Y"}

    def test_json_format(self):
        """JSON形式も読み込み可能"""
        import json
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump({"characters": ["J1", "J2"]}, f)
            temp_path = f.name
        
        try:
            loaded = load_character_dict(temp_path)
            assert loaded == {"J1", "J2"}
        finally:
            Path(temp_path).unlink(missing_ok=True)