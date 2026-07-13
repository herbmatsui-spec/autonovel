from __future__ import annotations

import logging
import os
from collections import OrderedDict
from typing import Any, Dict, Optional, Tuple

import yaml
from jinja2 import DictLoader, Environment, FileSystemLoader, select_autoescape

from config import PROMPT_TEMPLATES
from src.domain.types import BookId

logger = logging.getLogger(__name__)

from dataclasses import dataclass, field
from time import time


@dataclass
class CachedTemplate:
    """テンプレートのキャッシュエントリーを保持する。"""
    source: str
    mtime: float
    metadata: Dict[str, Any]
    pure_template: str
    timestamp: float = field(default_factory=time)

class PromptRegistry:
    """
    世界クラスの PromptOps 実装:
    プロンプトテンプレートをファイル、DB、およびメモリ上の設定から階層的に解決し、
    動的なバージョニングと A/B テストをサポートする。
    """
    def __init__(self, templates_dir: Optional[str] = None, db_manager: Any = None):
        if templates_dir is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            self.templates_dir = current_dir
        else:
            self.templates_dir = templates_dir

        self.db_manager = db_manager

        # キャッシュ用ストレージ (template_name -> CachedTemplate)
        self._template_cache: OrderedDict[str, CachedTemplate] = OrderedDict()
        from config.settings import ConfigManager

        # 設定ファイルから最大キャッシュサイズを取得
        self._cache_max_size = ConfigManager.get_config().prompt_cache_max_size

        # メトリクス追跡用
        self._metrics: Dict[str, Dict[str, Any]] = {}

        # templates/ 以下のサブディレクトリを自動的にロードする
        # templates/ 以下のサブディレクトリを自動的にロードする
        normalized_dir = os.path.abspath(self.templates_dir)
        search_paths = []

        # 1. templates_dir 自体を再帰的に探索して search_paths に追加
        for root, dirs, _ in os.walk(normalized_dir):
            search_paths.append(root)

        # 2. templates/ サブディレクトリがある場合はそれを優先的な探索パスとして追加
        templates_root = os.path.join(normalized_dir, "templates")
        if os.path.exists(templates_root):
            sub_paths = []
            for root, dirs, _ in os.walk(templates_root):
                sub_paths.append(root)
            search_paths = sub_paths + [p for p in search_paths if not p.startswith(templates_root)]

        self.fs_loader = FileSystemLoader(search_paths)
        self.dict_loader = DictLoader(PROMPT_TEMPLATES)

        self.jinja_env = Environment(
            loader=self.fs_loader,
            autoescape=select_autoescape()
        )

    def _update_cache_lru(self, template_name: str, cached_template: CachedTemplate):
        """LRUキャッシュを更新し、最大サイズを超えた場合は最古のエントリを削除する。"""
        if template_name in self._template_cache:
            self._template_cache.move_to_end(template_name)
        self._template_cache[template_name] = cached_template
        if len(self._template_cache) > self._cache_max_size:
            self._template_cache.popitem(last=False)

        # メトリクス追跡用
        self._metrics: Dict[str, Dict[str, Any]] = {}

    def _init_metric(self, template_name: str):
        """Initialize metrics for a template if not already present."""
        if template_name not in self._metrics:
            self._metrics[template_name] = {
                'hits': 0,
                'total_time_ms': 0.0,
                'avg_time_ms': 0.0,
                'last_accessed': None,
                'error_count': 0
            }

    def record_hit(self, template_name: str, duration_ms: float = 0.0, error: bool = False):
        """Record a template access hit with timing and error info."""
        self._init_metric(template_name)
        metric = self._metrics[template_name]
        metric['hits'] += 1
        metric['total_time_ms'] += duration_ms
        metric['avg_time_ms'] = metric['total_time_ms'] / metric['hits']
        metric['last_accessed'] = time.time()
        if error:
            metric['error_count'] += 1

    def get_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get current metrics snapshot."""
        return dict(self._metrics)

    def reset_metrics(self):
        """Reset all metrics."""
        self._metrics.clear()

    def clear_cache(self):
        """全キャッシュをクリアする。"""
        self._template_cache.clear()
        logger.info("PromptRegistry cache cleared.")

    def _get_template_source_sync(self, template_name: str) -> str:
        """
        同期的なソース解決。キャッシュを優先し、ファイル変更を検知して更新する。
        """

        # 拡張子補正
        if not template_name.endswith(".j2") and not template_name.endswith(".html") and "." not in template_name:
            template_name = f"{template_name}.j2"

        # --- キャッシュチェック ---
        if template_name in self._template_cache:
            cached = self._template_cache[template_name]

            # ファイルベースのテンプレートか確認し、mtimeをチェック
            # (DictLoader経由のものはmtimeが0として扱われる想定)
            if cached.mtime > 0:
                try:
                    # 実際のファイルパスを特定してmtimeを確認
                    _, filename, _ = self.fs_loader.get_source(self.jinja_env, template_name)
                    current_mtime = os.path.getmtime(filename)
                    if current_mtime < cached.mtime:
                        logger.debug(f"Cache hit for template: {template_name}")
                        self._update_cache_lru(template_name, cached)
                        return cached.source
                    logger.debug(f"Cache expired for template: {template_name} (mtime changed)")
                except Exception:
                    pass
            else:
                # DictLoader 由来のものは不変とみなし、そのまま返す
                logger.debug(f"Cache hit (DictLoader) for template: {template_name}")
                self._update_cache_lru(template_name, cached)
                return cached.source

        # --- ソース解決 ---
        source = None
        mtime = 0.0

        # 1. File System
        try:
            source, filename, _ = self.fs_loader.get_source(self.jinja_env, template_name)
            mtime = os.path.getmtime(filename)
        except Exception:
            pass

        # 2. DictLoader Fallback
        if source is None:
            try:
                for name in [template_name, template_name.replace(".j2", "")]:
                    try:
                        source, _, _ = self.dict_loader.get_source(self.jinja_env, name)
                        mtime = 0.0  # メモリ上のテンプレートはmtimeなし
                        break
                    except Exception:
                        continue
            except Exception:
                pass

        if source is None:
            raise FileNotFoundError(f"Prompt template '{template_name}' not found in any source.")

        # フロントマターを解析してキャッシュに保存
        metadata, pure_template = self.parse_frontmatter(source)
        cached_entry = CachedTemplate(
            source=source,
            mtime=mtime,
            metadata=metadata,
            pure_template=pure_template
        )
        self._update_cache_lru(template_name, cached_entry)

        return source

    def parse_frontmatter(self, source: str) -> Tuple[Dict[str, Any], str]:
        """YAML フロントマターを解析し、メタデータと本文を分離する。"""
        if source.startswith("---"):
            parts = source.split("---", 2)
            if len(parts) >= 3:
                try:
                    metadata = yaml.safe_load(parts[1]) or {}
                    return metadata, parts[2].strip()
                except Exception:
                    pass
        return {}, source

    def render(self, template_name: str, context: Dict[str, Any], book_id: Optional[BookId] = None) -> str:
        """同期レンダリング (DB override は無視される)"""
        # 拡張子補正
        if not template_name.endswith(".j2") and not template_name.endswith(".html") and "." not in template_name:
            template_name = f"{template_name}.j2"

        # キャッシュから pure_template を取得してコンパイルコストを削減
        if template_name in self._template_cache:
            cached = self._template_cache[template_name]
            try:
                if cached.mtime > 0:
                    _, filename, _ = self.fs_loader.get_source(self.jinja_env, template_name)
                    if os.path.getmtime(filename) <= cached.mtime:
                        return self.jinja_env.from_string(cached.pure_template).render(**context)
                else:
                    return self.jinja_env.from_string(cached.pure_template).render(**context)
            except Exception:
                pass

        # キャッシュミスまたは更新が必要な場合は通常ルートへ
        source = self._get_template_source_sync(template_name)
        metadata, pure_template = self.parse_frontmatter(source)
        return self.jinja_env.from_string(pure_template).render(**context)

    async def render_async(self, template_name: str, context: Dict[str, Any], book_id: Optional[BookId] = None) -> str:
        """
        非同期レンダリング。DB上の最新最適化プロンプトを優先的に適用する。
        """
        # 拡張子補正
        if not template_name.endswith(".j2") and not template_name.endswith(".html") and "." not in template_name:
            template_name = f"{template_name}.j2"

        source = None
        if book_id and self.db_manager:
            try:
                from src.backend.database.uow import UnitOfWork
                async with UnitOfWork(self.db_manager) as uow:
                    ver = await uow.prompt_versions.get_active_version(book_id, template_name)
                    if ver:
                        source = ver["content"]
            except Exception as e:
                logger.error(f"Error fetching prompt version from DB: {e}")

        if source is None:
            source = self._get_template_source_sync(template_name)

        metadata, pure_template = self.parse_frontmatter(source)
        return self.jinja_env.from_string(pure_template).render(**context)

