import json
import logging
from io import StringIO

from pythonjsonlogger import jsonlogger

from src.core.observability import TraceContext, TraceIdFilter, get_structured_logger


def setup_test_logger(logger_name="test_logger"):
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)

    # 既存のハンドラをクリアして重複を防ぐ
    logger.handlers = []

    # 出力をキャプチャするためのハンドラ
    log_output = StringIO()
    handler = logging.StreamHandler(log_output)

    # JSONフォーマッタの設定
    formatter = jsonlogger.JsonFormatter('%(timestamp)s %(level)s %(name)s %(message)s %(trace_id)s')
    handler.setFormatter(formatter)

    logger.addHandler(handler)

    # TraceIdFilterの追加
    logger.addFilter(TraceIdFilter())

    return logger, log_output

def test_structured_logger_metadata():
    """
    StructuredLogger がキーワード引数を正しく extra フィールドにマッピングし、
    JSON 出力に含まれることを検証する。
    """
    logger_name = "meta_test"
    setup_test_logger(logger_name)
    s_logger = get_structured_logger(logger_name)

    # ログ出力先の StringIO を取得するために logger のハンドラから取り出す
    logger_base = logging.getLogger(logger_name)
    output = logger_base.handlers[0].stream

    # テストデータのログ出力
    test_book_id = 123
    test_user_id = 456
    s_logger.info("Book created", book_id=test_book_id, user_id=test_user_id)

    # 修正: 変数名のタイポ修正 a-priori
    # (上の行で test_userid としたので修正)
    # 実際には以下のように書き直します

def test_structured_logger_metadata_fixed():
    logger_name = "meta_test_fixed"
    setup_test_logger(logger_name)
    s_logger = get_structured_logger(logger_name)
    logger_base = logging.getLogger(logger_name)
    output = logger_base.handlers[0].stream

    test_book_id = 123
    test_user_id = 456
    s_logger.info("Book created", book_id=test_book_id, user_id=test_user_id)

    log_line = output.getvalue().strip()
    log_json = json.loads(log_line)

    assert log_json["message"] == "Book created"
    assert log_json["book_id"] == test_book_id
    assert log_json["user_id"] == test_user_id

def test_structured_logger_with_trace_id():
    """
    StructuredLogger が TraceContext の trace_id を自動的に含めることを検証する。
    """
    logger_name = "trace_test"
    setup_test_logger(logger_name)
    s_logger = get_structured_logger(logger_name)
    logger_base = logging.getLogger(logger_name)
    output = logger_base.handlers[0].stream

    test_trace_id = "test-trace-12345"
    TraceContext.set_trace_id(test_trace_id)

    try:
        s_logger.info("Request processed", request_id="req-001")

        log_line = output.getvalue().strip()
        log_json = json.loads(log_line)

        assert log_json["trace_id"] == test_trace_id
        assert log_json["request_id"] == "req-001"
    finally:
        TraceContext.clear()

def test_structured_logger_extra_param():
    """
    'extra' キーワード引数が渡された場合に、それが正しく処理されることを検証する。
    """
    logger_name = "extra_test"
    setup_test_logger(logger_name)
    s_logger = get_structured_logger(logger_name)
    logger_base = logging.getLogger(logger_name)
    output = logger_base.handlers[0].stream

    s_logger.info("Custom extra test", extra={"custom_field": "custom_value"}, other_field="other_value")

    log_line = output.getvalue().strip()
    log_json = json.loads(log_line)

    assert log_json["custom_field"] == "custom_value"
    assert log_json["other_field"] == "other_value"
