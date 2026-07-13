#!/usr/bin/env python
"""Prompt Registry - Wrapper for PromptManager with metrics collection"""

import time
from typing import Any, Dict, Optional

from prompts.manager import PromptManager


class PromptRegistry:
    """
    PromptManagerをラップし、使用統計を収集するレジストリ。
    キャッシュヒット率・レンダリング時間を追跡します。
    """

    def __init__(self, prompt_manager: PromptManager):
        self._pm = prompt_manager
        self._metrics: Dict[str, Dict[str, Any]] = {}
        self._enabled = True

    def get(self, template_name: str, **variables) -> str:
        """
        テンプレートを取得し、レンダリング時間とヒット数を記録します。
        
        Args:
            template_name: テンプレート名
            **variables: テンプレート変数
            
        Returns:
            レンダリングされたテンプレート文字列
        """
        if not self._enabled:
            return self._pm.get_template(template_name).render(**variables)

        start_time = time.perf_counter()
        try:
            template = self._pm.get_template(template_name)
            rendered = template.render(**variables)
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            # メトリクスを更新
            if template_name not in self._metrics:
                self._metrics[template_name] = {
                    'hits': 0,
                    'total_time_ms': 0.0,
                    'avg_time_ms': 0.0,
                    'last_accessed': time.time()
                }

            metrics = self._metrics[template_name]
            metrics['hits'] += 1
            metrics['total_time_ms'] += elapsed_ms
            metrics['avg_time_ms'] = metrics['total_time_ms'] / metrics['hits']
            metrics['last_accessed'] = time.time()

            return rendered
        except Exception as e:
            # エラー時もメトリクスを記録（失敗として）
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            if template_name not in self._metrics:
                self._metrics[template_name] = {
                    'hits': 0,
                    'total_time_ms': 0.0,
                    'avg_time_ms': 0.0,
                    'error_count': 0,
                    'last_accessed': time.time()
                }

            metrics = self._metrics[template_name]
            metrics['hits'] += 1
            metrics['total_time_ms'] += elapsed_ms
            metrics['avg_time_ms'] = metrics['total_time_ms'] / metrics['hits']
            metrics['error_count'] = metrics.get('error_count', 0) + 1
            metrics['last_accessed'] = time.time()

            raise e

    def get_metrics(self) -> Dict[str, Dict[str, Any]]:
        """収集されたメトリクスを返す（コピー）."""
        import copy
        return copy.deepcopy(self._metrics)

    def reset_metrics(self, template_name: Optional[str] = None) -> None:
        """メトリクスをリセットする。
        
        Args:
            template_name: 特定のテンプレートのみリセットする場合は指定。
                         Noneの場合はすべてのメトリクスをリセット。
        """
        if template_name is None:
            self._metrics.clear()
        elif template_name in self._metrics:
            del self._metrics[template_name]

    def enable(self):
        """メトリクス収集を有効にする."""
        self._enabled = True

    def disable(self):
        """メトリクス収集を無効にする."""
        self._enabled = False

    def is_enabled(self) -> bool:
        """メトリクス収集が有効かどうかを返す."""
        return self._enabled

    # PromptManagerのメソッドをデリゲート（passthrough）
    def __getattr__(self, name):
        return getattr(self._pm, name)


# エクスポート用
__all__ = ['PromptRegistry']
