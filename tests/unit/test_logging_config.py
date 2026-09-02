"""ロギング設定のユニットテスト。"""
from __future__ import annotations

import logging
import os
from unittest.mock import patch

from src.backend.logging_config import (
    _ContextFilter,
    _extra_attributes,
    _is_text_mode,
    _logger_levels_from_env,
    configure,
)


def test__extra_attributes():
    """アプリコンテキスト辞書を構築する。"""
    from src.backend.config import settings
    settings.APP_NAME = "TestApp"
    settings.APP_VERSION = "1.0.0"
    settings.APP_ENV = "local"

    result = _extra_attributes()
    assert result == {"app": "TestApp", "version": "1.0.0", "env": "local"}


def test__extra_attributes_default():
    """デフォルト値でアプリコンテキストを構築する。"""
    # settingsのモンキーパッチはfixtureで行うが、関数自体はエラーなく動作する
    result = _extra_attributes()
    assert isinstance(result, dict)
    assert "app" in result
    assert "version" in result
    assert "env" in result


def test__ContextFilter_init():
    """_ContextFilter はコンテキスト dict を保持する。"""
    filt = _ContextFilter({"app": "MyApp", "env": "test"})
    assert filt._context == {"app": "MyApp", "env": "test"}


def test__ContextFilter_filter():
    """_ContextFilter.filter はレコードにメタデータを注入する。"""
    filt = _ContextFilter({"app": "TestApp", "version": "1.0", "env": "local"})
    record = logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="test",
        args=None,
        exc_info=None,
    )
    assert filt.filter(record) is True
    assert record.app == "TestApp"
    assert record.env == "local"


def test__logger_levels_from_env_no_env():
    """環境変数がない場合は空 dict を返す。"""
    with patch.dict(os.environ, {}, clear=True):
        result = _logger_levels_from_env()
        assert result == {}


def test__logger_levels_from_env_with_valid():
    """有効な LOG_LEVEL_XXX 環境変数がある場合。"""
    with patch.dict(os.environ, {"LOG_LEVEL_MYLOGGER": "DEBUG"}, clear=True):
        result = _logger_levels_from_env()
        assert "mylogger" in result
        assert result["mylogger"] == logging.DEBUG


def test__logger_levels_from_env_invalid_value():
    """無効なログレベル値は文字列として保存される。

    getLevelName は認識できない値を "Level <string>" として返すため、
    例外は発生しない。ここは振る舞いを確認するだけ。
    """
    with patch.dict(os.environ, {"LOG_LEVEL_BAD": "NOT_A_LEVEL"}, clear=True):
        result = _logger_levels_from_env()
        # "Level NOT_A_LEVEL" が値としてセットされる
        assert "bad" in result


def test_configure_json_format(real_db_manager):
    """JSON フォーマットで configure() を実行する。"""
    # 既存ハンドラをクリア
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)

    os.environ["LOG_FORMAT"] = "json"
    os.environ.pop("LOG_LEVEL", None)

    configure()

    # JSONフォーマッタが設定されていることを確認
    handler = root.handlers[0]
    from pythonjsonlogger import json as jsonlogger
    assert isinstance(handler.formatter, jsonlogger.JsonFormatter)


def test_configure_text_format():
    """テキストフォーマットで configure() を実行する。"""
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)

    os.environ["LOG_FORMAT"] = "text"

    configure()

    # テキストフォーマッタが設定されていることを確認
    handler = root.handlers[0]
    assert handler.formatter._fmt is not None


def test_configure_with_log_level_env():
    """LOG_LEVEL_ENV でロガーのレベルを上書きする。"""
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)

    os.environ["LOG_LEVEL"] = "DEBUG"

    configure()

    # ルートロガーのレベルは DEBUG に設定される
    assert root.level == logging.DEBUG


def test_configure_noise_suppression():
    """うるさいサードパーティロガーのノイズを抑制する。"""
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)

    os.environ["LOG_FORMAT"] = "text"

    configure()

    # uvicorn.access と sqlalchemy のレベルが WARNING になっていること
    assert logging.getLogger("uvicorn.access").level == logging.WARNING
    assert logging.getLogger("sqlalchemy.engine.Engine").level == logging.WARNING


def test__is_text_mode():
    """_is_text_mode は False を返す。"""
    result = _is_text_mode()
    assert result is False
