"""構造化ロギング設定を提供するモジュール (Phase 5: Step 51-54).

python-json-logger を用いた JSON ログ出力を既定とし、プレーンテキスト
フォールバックも備える。コンテキスト項目 (app, env, version) を常時付与し、
ロガー別のログレベル制御も行う。

環境変数:
    LOG_LEVEL  : ルートロガーのレベル (既定 INFO)
    LOG_FORMAT : ``json`` (既定) または ``text`` を指定してフォーマット切替
    APP_ENV    : デプロイ環境識別子 (local/staging/production 等。任意)
    LOG_LEVEL_<NAME> : 特定ロガー ``<NAME>`` のレベルを上書き (例: LOG_LEVEL_HUEY=DEBUG)
"""
from __future__ import annotations

import logging
import logging.config
import os
import sys
from typing import Any

from src.backend.config import settings


def _extra_attributes() -> dict[str, Any]:
    """ログレコードへ常時付与するアプリコンテキストを構築する。"""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "env": settings.APP_ENV,
    }


class _ContextFilter(logging.Filter):
    """全レコードへアプリメタデータ (app/version/env) を注入するグローバルフィルタ。"""

    def __init__(self, context: dict[str, Any]) -> None:
        super().__init__()
        self._context = context

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: A003 - logging API
        for key, value in self._context.items():
            # 既存の属性を上書きしない
            setattr(record, key, getattr(record, key, value))
        return True


def _logger_levels_from_env() -> dict[str, int]:
    """``LOG_LEVEL_<NAME>`` 形式の環境変数からロガー別レベルを抽出する。"""
    prefix = "LOG_LEVEL_"
    levels: dict[str, int] = {}
    for key, value in os.environ.items():
        if key.startswith(prefix) and key != "LOG_LEVEL":
            logger_name = key[len(prefix) :].lower()
            try:
                levels[logger_name] = logging.getLevelName(value.upper())
            except (TypeError, ValueError):
                continue
    return levels


def configure() -> None:
    """ルートロガーへ環境に応じたハンドラを設定する。

    既定で JSON 形式 (python-json-logger) を出力する。``LOG_FORMAT=text`` の
    場合はプレーンテキストへフォールバックする。また ``LOG_LEVEL_<NAME>``
    で個別ロガー (例: huey, src.backend) のレベルを上書きできる。
    """
    level = os.getenv("LOG_LEVEL", settings.LOG_LEVEL).upper()
    log_format = os.getenv("LOG_FORMAT", settings.LOG_FORMAT).lower()

    root = logging.getLogger()
    # 既存ハンドラをクリアして重複出力を防止
    for _h in list(root.handlers):
        root.removeHandler(_h)

    formatter: logging.Formatter
    handler: logging.Handler
    if log_format == "text" or _is_text_mode():
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s [%(app)s/%(env)s]: %(message)s"
        )
    else:
        try:
            try:
                from pythonjsonlogger import json as jsonlogger  # type: ignore[import-not-found]
            except ImportError:
                from pythonjsonlogger import jsonlogger  # type: ignore[import-not-found,no-redef]
        except ImportError:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter(
                "%(asctime)s %(levelname)s %(name)s: %(message)s"
            )
        else:
            handler = logging.StreamHandler(sys.stdout)
            formatter = jsonlogger.JsonFormatter(
                (
                    "%(asctime)s %(levelname)s %(name)s %(message)s "
                    "%(app)s %(version)s %(env)s"
                ),
                rename_fields={
                    "asctime": "timestamp",
                    "levelname": "level",
                    "name": "logger",
                    "app": "app",
                    "version": "version",
                    "env": "env",
                },
            )

    handler.setFormatter(formatter)
    root.addHandler(handler)
    root.setLevel(level)

    # アプリメタデータを全レコードへ注入
    context_filter = _ContextFilter(_extra_attributes())
    root.addFilter(context_filter)

    # ロガー別レベル上書きを適用
    for logger_name, logger_level in _logger_levels_from_env().items():
        logging.getLogger(logger_name).setLevel(logger_level)

    # 既知のうるさいサードパーティロガーのノイズを抑制 (既定 DEBUG 未満)
    for noisy in ("uvicorn.access", "sqlalchemy.engine.Engine"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def _is_text_mode() -> bool:
    """stdout が TTY で環境上 JSON を出していない場合などにテキスト化するか判断。

    CI やファイル保存を想定し JSON を維持できるよう、明示的に LOG_FORMAT=text
    でない限り TTY 判定のみでは切り替えない (将来の拡張ポイント)。
    """
    return False


__all__: list[str] = ["configure"]
