from __future__ import annotations

import logging
import os
from collections import OrderedDict
from typing import Any, Optional, Tuple, Union

import yaml
from dataclasses import dataclass, field
from time import time
from jinja2 import DictLoader, Environment, FileSystemLoader, select_autoescape
from jinja2.exceptions import TemplateError, UndefinedError

from prompts.metrics import IMetricsCollector, InMemoryCollector
from config.project_context import PROMPT_TEMPLATES
from config.settings import BASE_DIR
from prompts.exceptions import PromptDbError, PromptRenderingError, PromptTemplateNotFoundError
from prompts.schemas import PromptContext
from src.domain.types import BookId

logger = logging.getLogger(__name__)


@dataclass
class CachedTemplate:
    """テンプレートのキャッシュエントリーを保持する。"""

    source: str
    mtime: float
    metadata: dict[str, Any]
    pure_template: str
    timestamp: float = field(default_factory=time)


class PromptRegistry:
    """
    世界クラスの PromptOps 実装:
    プロンプトテンプレートをファイル、DB、およびメモリ上の設定から階層的に解決し、
    動的なバージョニングと A/B テストをサポートする。
    """

    def __init__(
        self,
        templates_dir: Optional[str] = None,
        db_manager: Any = None,
        metrics_collector: Optional[IMetricsCollector] = None,
    ):
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

        # メトリクスコレクタ (DI)
        self.metrics_collector: IMetricsCollector = metrics_collector or InMemoryCollector()

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
            autoescape=select_autoescape(
                enabled_extensions=('html', 'xml'),
                default_for_string=False,
                default=False,
            ),
        )

    def _update_cache_lru(self, template_name: str, cached_template: CachedTemplate) -> None:
        """LRUキャッシュを更新し、最大サイズを超えた場合は最古のエントリを削除する。"""
        if template_name in self._template_cache:
            self._template_cache.move_to_end(template_name)
        self._template_cache[template_name] = cached_template
        if len(self._template_cache) > self._cache_max_size:
            self._template_cache.popitem(last=False)

    def record_hit(self, template_name: str, duration_ms: float = 0.0, error: bool = False) -> None:
        """Record a template access hit with timing and error info."""
        self.metrics_collector.record_hit(template_name, duration_ms, error)

    def get_metrics(self) -> dict[str, Any]:
        """Get current metrics snapshot."""
        return {k: v.__dict__ for k, v in self.metrics_collector.get_metrics().items()}

    def reset_metrics(self) -> None:
        """Reset all metrics."""
        self.metrics_collector.reset_metrics()

    def clear_cache(self) -> None:
        """全キャッシュをクリアする。"""
        self._template_cache.clear()
        logger.info("PromptRegistry cache cleared.")

    def _get_template_source_sync(self, template_name: str) -> str:
        """
        同期的なソース解決。キャッシュを優先し、ファイル変更を検知して更新する。
        """

        # 拡張子補正
        if (
            not template_name.endswith(".j2")
            and not template_name.endswith(".html")
            and "." not in template_name
        ):
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
                except (OSError, TemplateNotFound) as e:
                    logger.debug(f"Template mtime check skipped for {template_name}: {e}")
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
        except (TemplateNotFound, OSError) as e:
            logger.debug(f"Template '{template_name}' not found on filesystem: {e}")

        # 2. DictLoader Fallback
        if source is None:
            for name in [template_name, template_name.replace(".j2", "")]:
                try:
                    source, _, _ = self.dict_loader.get_source(self.jinja_env, name)
                    mtime = 0.0  # メモリ上のテンプレートはmtimeなし
                    break
                except (TemplateNotFound, KeyError):
                    continue

        if source is None:
            raise PromptTemplateNotFoundError(
                f"Prompt template '{template_name}' not found in any source.", template_name
            )

        # フロントマターを解析してキャッシュに保存
        metadata, pure_template = self.parse_frontmatter(source)
        cached_entry = CachedTemplate(
            source=source, mtime=mtime, metadata=metadata, pure_template=pure_template
        )
        self._update_cache_lru(template_name, cached_entry)

        return source

    def parse_frontmatter(self, source: str) -> Tuple[dict[str, Any], str]:
        """YAML フロントマターを解析し、メタデータと本文を分離する。"""
        if source.startswith("---"):
            parts = source.split("---", 2)
            if len(parts) >= 3:
                try:
                    metadata = yaml.safe_load(parts[1]) or {}
                    return metadata, parts[2].strip()
                except Exception as e:
                    logger.warning(f"Failed to parse YAML frontmatter: {e}")
        return {}, source


    def _prepare_context(
        self, context: Optional[Union[dict[str, Any], PromptContext]] = None, kwargs: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """PydanticモデルまたはdictをJinja2用のdictに変換し、kwargsをマージ。"""
        if context is None:
            ctx = {}
        elif isinstance(context, PromptContext):
            ctx = context.model_dump()
        elif isinstance(context, dict):
            ctx = dict(context)
        else:
            ctx = {}
        if kwargs:
            ctx.update(kwargs)
        return ctx

    def render(
        self,
        template_name: str,
        context: Optional[Union[dict[str, Any], PromptContext]] = None,
        book_id: Optional[BookId] = None,
        **kwargs: Any,
    ) -> str:
        """同期レンダリング (DB override は無視される)"""
        # 拡張子補正
        if (
            not template_name.endswith(".j2")
            and not template_name.endswith(".html")
            and "." not in template_name
        ):
            template_name = f"{template_name}.j2"

        ctx = self._prepare_context(context, kwargs)

        # キャッシュから pure_template を取得してコンパイルコストを削減
        if template_name in self._template_cache:
            cached = self._template_cache[template_name]
            try:
                if cached.mtime > 0:
                    _, filename, _ = self.fs_loader.get_source(self.jinja_env, template_name)
                    if os.path.getmtime(filename) <= cached.mtime:
                        return self.jinja_env.from_string(cached.pure_template).render(**ctx)
                else:
                    return self.jinja_env.from_string(cached.pure_template).render(**ctx)
            except (TemplateError, UndefinedError) as e:
                self.record_hit(template_name, error=True)
                raise PromptRenderingError(
                    f"Failed to render template '{template_name}': {e}",
                    template_name,
                    missing_keys=getattr(e, "missing_keys", None),
                ) from e
            except Exception:
                pass

        # キャッシュミスまたは更新が必要な場合は通常ルートへ
        start_time = time()
        try:
            source = self._get_template_source_sync(template_name)
            metadata, pure_template = self.parse_frontmatter(source)
            result = self.jinja_env.from_string(pure_template).render(**ctx)
            self.record_hit(template_name, duration_ms=(time() - start_time) * 1000)
            return result
        except (TemplateError, UndefinedError) as e:
            self.record_hit(template_name, duration_ms=(time() - start_time) * 1000, error=True)
            raise PromptRenderingError(
                f"Failed to render template '{template_name}': {e}",
                template_name,
                missing_keys=getattr(e, "missing_keys", None),
            ) from e
        except Exception:
            self.record_hit(template_name, duration_ms=(time() - start_time) * 1000, error=True)
            raise

    async def render_async(
        self,
        template_name: str,
        context: Optional[Union[dict[str, Any], PromptContext]] = None,
        book_id: Optional[BookId] = None,
        **kwargs: Any,
    ) -> str:
        """
        非同期レンダリング。DB上の最新最適化プロンプトを優先的に適用する。
        """
        # 拡張子補正
        if (
            not template_name.endswith(".j2")
            and not template_name.endswith(".html")
            and "." not in template_name
        ):
            template_name = f"{template_name}.j2"

        ctx = self._prepare_context(context, kwargs)


        source = None
        if book_id and self.db_manager:
            try:
                from src.backend.database.uow import UnitOfWork

                async with UnitOfWork(self.db_manager) as uow:
                    ver = await uow.prompt_versions.get_active_prompt_version(book_id, template_name)
                    if ver:
                        source = ver["content"]
            except Exception as e:
                logger.error(f"Error fetching prompt version from DB: {e}")
                raise PromptDbError(
                    f"Failed to fetch prompt version from DB: {e}", template_name, book_id=book_id
                ) from e

        start_time = time()
        try:
            if source is None:
                source = self._get_template_source_sync(template_name)

            metadata, pure_template = self.parse_frontmatter(source)
            result = self.jinja_env.from_string(pure_template).render(**ctx)
            self.record_hit(template_name, duration_ms=(time() - start_time) * 1000)
            return result
        except (TemplateError, UndefinedError) as e:
            self.record_hit(template_name, duration_ms=(time() - start_time) * 1000, error=True)
            raise PromptRenderingError(
                f"Failed to render template '{template_name}': {e}",
                template_name,
                missing_keys=getattr(e, "missing_keys", None),
            ) from e
        except Exception:
            self.record_hit(template_name, duration_ms=(time() - start_time) * 1000, error=True)
            raise
