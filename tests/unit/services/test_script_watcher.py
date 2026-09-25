"""Tests for script watcher service."""
from __future__ import annotations

import pytest
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.services.script_watcher import ScriptWatcher, WatchConfig, create_script_watcher
from src.pipeline.emotional_residue import EmotionType
from src.stores.vector_store import RedisVectorStore


class TestScriptWatcher:
    """スクリプト監視サービステスト"""

    @pytest.fixture
    def temp_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def mock_vector_store(self):
        import fakeredis
        redis_client = fakeredis.FakeRedis(decode_responses=True)
        store = RedisVectorStore(skip_connection_check=True)
        store.client = redis_client
        return store

    @pytest.fixture
    def config(self, temp_dir):
        return WatchConfig(
            script_root=temp_dir,
            pattern="episode_*.md",
            poll_interval=0.1,
        )

    @pytest.fixture
    def watcher(self, config, mock_vector_store):
        return ScriptWatcher(
            config=config,
            vector_store=mock_vector_store,
            character_dict={"A", "B"},
        )

    def test_extract_episode_number(self, watcher):
        """エピソード番号抽出テスト"""
        assert watcher._extract_episode_number(Path("episode_14.md")) == 14
        assert watcher._extract_episode_number(Path("ep14.md")) == 14
        assert watcher._extract_episode_number(Path("14.md")) == 14
        assert watcher._extract_episode_number(Path("episode_01.md")) == 1
        assert watcher._extract_episode_number(Path("readme.md")) is None

    def test_compute_hash(self, watcher, temp_dir):
        """ハッシュ計算テスト"""
        file_path = temp_dir / "test.md"
        file_path.write_text("test content", encoding="utf-8")
        
        hash1 = watcher._compute_hash(file_path)
        assert len(hash1) == 64  # SHA256 hex
        
        # 同じ内容なら同じハッシュ
        hash2 = watcher._compute_hash(file_path)
        assert hash1 == hash2
        
        # 内容変更でハッシュ変化
        file_path.write_text("different content", encoding="utf-8")
        hash3 = watcher._compute_hash(file_path)
        assert hash1 != hash3

    def test_process_file_no_episode(self, watcher, temp_dir):
        """エピソード番号なしファイルはスキップ"""
        file_path = temp_dir / "readme.md"
        file_path.write_text("# Readme\n", encoding="utf-8")
        
        result = watcher._process_file(file_path)
        assert result is False

    def test_process_file_with_annotation(self, watcher, temp_dir, mock_vector_store):
        """アノテーション付きファイル処理"""
        file_path = temp_dir / "episode_14.md"
        content = """---
beats:
  - source: "A"
    target: "B"
    emotion: "fear"
    delta: 0.8
    cause: "ep14 betrayal"
---
A「行くぞ」
[beat:fear+0.6 cause="ep14 betrayal"]
"""
        file_path.write_text(content, encoding="utf-8")
        
        result = watcher._process_file(file_path)
        assert result is True
        
        # ベクトルストアに保存されたか確認
        stored = mock_vector_store.get_latest("annotation", ("A", "B"))
        assert stored is not None
        assert stored.get_value("A", "B", EmotionType.FEAR) > 0

    def test_hash_change_detection(self, watcher, temp_dir, mock_vector_store):
        """ハッシュ変更検出テスト"""
        file_path = temp_dir / "episode_14.md"
        content = """---
beats:
  - source: "A"
    target: "B"
    emotion: "fear"
    delta: 0.5
    cause: "test"
---
"""
        file_path.write_text(content, encoding="utf-8")
        
        # 初回処理
        result1 = watcher._process_file(file_path)
        assert result1 is True
        
        # 同じ内容で再処理 → スキップされる
        result2 = watcher._process_file(file_path)
        assert result2 is False
        
        # 内容変更
        content2 = content.replace("0.5", "0.8")
        file_path.write_text(content2, encoding="utf-8")
        
        # 再処理 → 変更検出される
        result3 = watcher._process_file(file_path)
        assert result3 is True

    def test_scan_once(self, watcher, temp_dir, mock_vector_store):
        """1回スキャンテスト"""
        # 単一ファイル作成（複数だと遅い可能性）
        (temp_dir / "episode_14.md").write_text(
            """---
beats:
  - source: "A"
    target: "B"
    emotion: "fear"
    delta: 0.5
    cause: "test"
---""", encoding="utf-8"
        )
        (temp_dir / "readme.md").write_text("# Readme", encoding="utf-8")
        
        processed = watcher.scan_once()
        assert processed == 1

    def test_force_process(self, watcher, temp_dir, mock_vector_store):
        """強制処理テスト"""
        file_path = temp_dir / "episode_14.md"
        content = """---
beats:
  - source: "A"
    target: "B"
    emotion: "fear"
    delta: 0.5
    cause: "test"
---"""
        file_path.write_text(content, encoding="utf-8")
        
        # 初回処理
        watcher._process_file(file_path)
        
        # 強制処理（ハッシュ無視）
        result = watcher.force_process(file_path)
        assert result is True

    def test_validation_failure_skips_persist(self, watcher, temp_dir, mock_vector_store):
        """検証失敗時は永続化スキップ"""
        file_path = temp_dir / "episode_14.md"
        # 不明キャラを含む
        content = """---
beats:
  - source: "X"  # 不明キャラ
    target: "B"
    emotion: "fear"
    delta: 0.5
    cause: "test"
---"""
        file_path.write_text(content, encoding="utf-8")
        
        result = watcher._process_file(file_path)
        assert result is False
        
        # 永続化されていないことを確認
        stored = mock_vector_store.get_latest("annotation", ("X", "B"))
        assert stored is None


class TestCreateScriptWatcher:
    """create_script_watcher ヘルパーテスト"""

    @pytest.fixture
    def temp_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def mock_vector_store(self):
        import fakeredis
        redis_client = fakeredis.FakeRedis(decode_responses=True)
        store = RedisVectorStore(skip_connection_check=True)
        store.client = redis_client
        return store

    def test_create_script_watcher(self, temp_dir, mock_vector_store):
        """ヘルパー関数テスト"""
        watcher = create_script_watcher(
            script_root=str(temp_dir),
            vector_store=mock_vector_store,
            character_dict={"A", "B"},
            poll_interval=0.1,
        )
        
        assert isinstance(watcher, ScriptWatcher)
        assert watcher.config.script_root == temp_dir
        assert watcher.config.poll_interval == 0.1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])