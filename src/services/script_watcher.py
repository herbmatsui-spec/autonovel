"""Script file watcher service for automatic annotation persistence."""
from __future__ import annotations

import hashlib
import logging
import time
from pathlib import Path
from typing import Optional, Callable, Dict, Set
from dataclasses import dataclass

from src.annotations.integrated_parser import parse_script, BeatParser
from src.annotations.persistence import AnnotationPersistence
from src.annotations.validator import BeatValidator
from src.pipeline.character_dict import load_character_dict
from src.stores.vector_store import VectorStore
from src.stores.graph_store import GraphStore
from src.stores.event_log import EventLogStore

logger = logging.getLogger(__name__)


@dataclass
class WatchConfig:
    """監視設定"""
    script_root: Path
    pattern: str = "episode_*.md"
    poll_interval: float = 30.0  # seconds
    enabled: bool = True


class ScriptWatcher:
    """脚本ファイル監視・自動永続化サービス"""
    
    def __init__(
        self,
        config: WatchConfig,
        vector_store: VectorStore,
        graph_store: Optional[GraphStore] = None,
        log_store: Optional[EventLogStore] = None,
        character_dict: Optional[Set[str]] = None,
        on_change: Optional[Callable[[int, str], None]] = None,
    ):
        self.config = config
        self.vector_store = vector_store
        self.graph_store = graph_store
        self.log_store = log_store
        self.character_dict = character_dict or load_character_dict()
        self.on_change = on_change
        
        # 内部状態
        self._file_hashes: Dict[Path, str] = {}
        self._parser = BeatParser(self.character_dict)
        self._persistence = AnnotationPersistence(vector_store, graph_store, log_store)
        self._validator = BeatValidator(self.character_dict)
        self._running = False
    
    def _compute_hash(self, file_path: Path) -> str:
        """ファイルのSHA256ハッシュを計算"""
        try:
            content = file_path.read_text(encoding="utf-8")
            return hashlib.sha256(content.encode("utf-8")).hexdigest()
        except Exception as e:
            logger.warning(f"Failed to read {file_path}: {e}")
            return ""
    
    def _extract_episode_number(self, file_path: Path) -> Optional[int]:
        """ファイル名からエピソード番号を抽出
        
        対応パターン:
        - episode_14.md
        - ep14.md
        - 14.md
        """
        name = file_path.stem.lower()
        
        # episode_N パターン
        if name.startswith("episode_"):
            try:
                return int(name.split("_")[1])
            except (IndexError, ValueError):
                pass
        
        # epN パターン
        if name.startswith("ep"):
            try:
                return int(name[2:])
            except ValueError:
                pass
        
        # 数字のみ
        if name.isdigit():
            return int(name)
        
        return None
    
    def _process_file(self, file_path: Path) -> bool:
        """単一ファイルを処理してアノテーションを永続化
        
        Returns:
            処理したかどうか（変更があった場合True）
        """
        episode = self._extract_episode_number(file_path)
        if episode is None:
            logger.debug(f"Episode number not found in {file_path.name}")
            return False
        
        # ハッシュチェック
        current_hash = self._compute_hash(file_path)
        if not current_hash:
            return False
        
        if self._file_hashes.get(file_path) == current_hash:
            return False  # 変更なし
        
        # ファイル読み込み・パース
        try:
            script_text = file_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to read {file_path}: {e}")
            return False
        
        # パース・検証・永続化
        try:
            parsed = self._parser.parse_script(script_text, episode)
            
            # 検証
            result = self._validator.validate(parsed.beats, self.character_dict)
            if not result.is_valid:
                logger.warning(f"Validation failed for {file_path}: {result.errors}")
                # エラーがあっても警告のみで継続（永続化はスキップ）
                for error in result.errors:
                    logger.warning(f"  {error}")
                for warning in result.warnings:
                    logger.warning(f"  {warning}")
                if not result.is_valid:
                    return False
            
            # 永続化
            if parsed.beats:
                count = self._persistence.persist_beats(parsed.beats, episode)
                logger.info(f"Persisted {count} annotation beats from {file_path.name} (ep{episode})")
                
                # コールバック実行
                if self.on_change:
                    try:
                        self.on_change(episode, file_path.name)
                    except Exception as e:
                        logger.warning(f"on_change callback failed: {e}")
            
            # ハッシュ更新
            self._file_hashes[file_path] = current_hash
            return True
            
        except Exception as e:
            logger.error(f"Failed to process {file_path}: {e}")
            return False
    
    def scan_once(self) -> int:
        """1回分のスキャンを実行
        
        Returns:
            処理したファイル数
        """
        processed = 0
        script_root = self.config.script_root
        
        if not script_root.exists():
            logger.warning(f"Script root not found: {script_root}")
            return 0
        
        for file_path in script_root.glob(self.config.pattern):
            if file_path.is_file():
                if self._process_file(file_path):
                    processed += 1
        
        return processed
    
    def start(self) -> None:
        """監視ループ開始（ブロッキング）"""
        self._running = True
        logger.info(f"Script watcher started: {self.config.script_root} (interval: {self.config.poll_interval}s)")
        
        while self._running:
            try:
                processed = self.scan_once()
                if processed > 0:
                    logger.debug(f"Processed {processed} files")
            except Exception as e:
                logger.error(f"Scan error: {e}")
            
            time.sleep(self.config.poll_interval)
    
    def stop(self) -> None:
        """監視停止"""
        self._running = False
        logger.info("Script watcher stopped")
    
    def force_process(self, file_path: Path) -> bool:
        """指定ファイルを強制処理（ハッシュチェック無視）"""
        # ハッシュをリセットして強制処理
        if file_path in self._file_hashes:
            del self._file_hashes[file_path]
        return self._process_file(file_path)


class PollingScriptWatcher(ScriptWatcher):
    """ポーリングベースのファイル監視（watchdog非依存）"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        logger.info("Using polling-based file watcher")


def create_script_watcher(
    script_root: str,
    vector_store: VectorStore,
    graph_store: Optional[GraphStore] = None,
    log_store: Optional[EventLogStore] = None,
    character_dict: Optional[Set[str]] = None,
    poll_interval: float = 30.0,
    pattern: str = "episode_*.md",
    on_change: Optional[Callable[[int, str], None]] = None,
) -> ScriptWatcher:
    """ScriptWatcher作成ヘルパー"""
    config = WatchConfig(
        script_root=Path(script_root),
        pattern=pattern,
        poll_interval=poll_interval,
    )
    return PollingScriptWatcher(
        config=config,
        vector_store=vector_store,
        graph_store=graph_store,
        log_store=log_store,
        character_dict=character_dict,
        on_change=on_change,
    )


__all__ = [
    "WatchConfig",
    "ScriptWatcher",
    "PollingScriptWatcher",
    "create_script_watcher",
]