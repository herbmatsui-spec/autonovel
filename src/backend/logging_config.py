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


class _SensitiveDataFilter(logging.Filter):
    """機密情報 (APIキー・トークン・パスワード等) をマスクするフィルタ。"""

    # マスク対象のキー名パターン (正規表現)
    SENSITIVE_KEY_PATTERNS = [
        r"(?i)(authorization)",
        r"(?i)(x-api-key)",
        r"(?i)(api[_-]?key)",
        r"(?i)(access[_-]?token)",
        r"(?i)(refresh[_-]?token)",
        r"(?i)(bearer)",
        r"(?i)(password)",
        r"(?i)(secret)",
        r"(?i)(client[_-]?secret)",
        r"(?i)(private[_-]?key)",
    ]

    # 値をマスクする際に先頭に残す文字数
    MASK_PREFIX_LENGTH = 4
    MASK_SUFFIX = "***"

    def filter(self, record: logging.LogRecord) -> bool:
        import re

        # msg 属性のマスキング
        if hasattr(record, "msg") and isinstance(record.msg, str):
            record.msg = self._mask_sensitive_data(record.msg)

        # args 属性のマスキング (タプルや辞書の場合)
        if hasattr(record, "args") and record.args:
            record.args = self._mask_args(record.args)

        return True

    def _mask_sensitive_data(self, text: str) -> str:
        """文字列内の機密情報をマスクする。"""
        import re

        # Authorization: Bearer <token> または Authorization: <token>
        text = re.sub(
            r"(?i)(authorization\s*[:=]\s*)(?:bearer\s+)?(\S+)",
            lambda m: m.group(1) + self._mask_value(m.group(2)),
            text,
        )
        # X-API-Key ヘッダー
        text = re.sub(
            r"(?i)(x-api-key\s*[:=]\s*)(\S+)",
            lambda m: m.group(1) + self._mask_value(m.group(2)),
            text,
        )
        # api_key クエリパラメータ
        text = re.sub(
            r"([?&]api[_-]?key=)([^&\s]+)",
            lambda m: m.group(1) + self._mask_value(m.group(2)),
            text,
        )
        # access_token クエリパラメータ
        text = re.sub(
            r"(access[_-]?token=)([^&\s]+)",
            lambda m: m.group(1) + self._mask_value(m.group(2)),
            text,
        )
        # refresh_token クエリパラメータ
        text = re.sub(
            r"(refresh[_-]?token=)([^&\s]+)",
            lambda m: m.group(1) + self._mask_value(m.group(2)),
            text,
        )
        # Bearer トークン (Authorization ヘッダーとは独立して存在する場合)
        text = re.sub(
            r"(?i)(bearer\s+)(\S+)",
            lambda m: m.group(1) + self._mask_value(m.group(2)),
            text,
        )
        # パスワード系
        text = re.sub(
            r"(?i)(password\s*[:=]\s*)(\S+)",
            lambda m: m.group(1) + self._mask_value(m.group(2)),
            text,
        )
        # シークレット系
        text = re.sub(
            r"(?i)(secret\s*[:=]\s*)(\S+)",
            lambda m: m.group(1) + self._mask_value(m.group(2)),
            text,
        )
        # client_secret
        text = re.sub(
            r"(?i)(client[_-]?secret\s*[:=]\s*)(\S+)",
            lambda m: m.group(1) + self._mask_value(m.group(2)),
            text,
        )
        # private_key
        text = re.sub(
            r"(?i)(private[_-]?key\s*[:=]\s*)(\S+)",
            lambda m: m.group(1) + self._mask_value(m.group(2)),
            text,
        )
        return text

    def _mask_value(self, value: str) -> str:
        """値をマスクする (先頭N文字のみ残す)。"""
        if len(value) <= self.MASK_PREFIX_LENGTH:
            return self.MASK_SUFFIX
        return value[: self.MASK_PREFIX_LENGTH] + self.MASK_SUFFIX

    def _mask_args(self, args: Any) -> Any:
        """args 内の機密データを再帰的にマスクする。"""
        if isinstance(args, dict):
            masked = {}
            for k, v in args.items():
                # キー名が機密情報を示す場合、値をマスク
                if self._is_sensitive_key(k):
                    masked[k] = self._mask_value(str(v))
                else:
                    masked[k] = self._mask_args(v)
            return masked
        elif isinstance(args, (list, tuple)):
            return type(args)(self._mask_args(v) for v in args)
        elif isinstance(args, str):
            return self._mask_sensitive_data(args)
        return args

    def _is_sensitive_key(self, key: str) -> bool:
        """キー名が機密情報を示すか判定する。"""
        import re
        sensitive_patterns = [
            r"(?i)^api[_-]?key$",
            r"(?i)^access[_-]?token$",
            r"(?i)^refresh[_-]?token$",
            r"(?i)^password$",
            r"(?i)^secret$",
            r"(?i)^secret$",
            r"(?i)^client[_-]?secret$",
            r"(?i)^private[_-]?key$",
            r"(?i)^token$",
            r"(?i)^bearer$",
            r"(?i)^authorization$",
            r"(?i)^x[_-]?api[_-]?key$",
            r"(?i)^jwt$",
            r"(?i)^session[_-]?id$",
            r"(?i)^csrf[_-]?token$",
        ]
        return any(re.match(pattern, str(key)) for pattern in sensitive_patterns)




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
            formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        else:
            handler = logging.StreamHandler(sys.stdout)
            formatter = jsonlogger.JsonFormatter(
                ("%(asctime)s %(levelname)s %(name)s %(message)s %(app)s %(version)s %(env)s"),
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
    # ハンドラーにもフィルタを追加（ロガーフィルタが呼ばれない環境対策）
    handler.addFilter(_ContextFilter(_extra_attributes()))
    handler.addFilter(_SensitiveDataFilter())
    root.addHandler(handler)
    root.setLevel(level)

    # ロガー別レベル上書きを適用
    for logger_name, logger_level in _logger_levels_from_env().items():
        logging.getLogger(logger_name).setLevel(logger_level)

    # 既知のうるさいサードパーティロガーのノイズを抑制 (既定 DEBUG 未満)
    for noisy in ("uvicorn.access", "sqlalchemy.engine.Engine"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def _is_text_mode() -> bool:
    """stdout が TTY で環境上 JSON を出していない場合などにテキスト化するか判断。"""
    return False


def get_logger(name: str) -> logging.Logger:
    """指定された名前の Logger を取得するヘルパー関数。"""
    return logging.getLogger(name)


__all__: list[str] = ["configure", "get_logger", "_is_text_mode"]
