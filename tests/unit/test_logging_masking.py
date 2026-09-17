"""機密情報マスキングフィルタのテスト"""

import logging
import pytest

from src.backend.logging_config import _SensitiveDataFilter, configure


@pytest.fixture(scope="session", autouse=True)
def setup_logging():
    """テストセッション開始時にログ設定を一度だけ実行"""
    configure()
    yield
    # テスト後にリセット
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)
    root.filters.clear()


class TestSensitiveDataFilter:
    """_SensitiveDataFilter のテスト"""

    @pytest.fixture
    def filter_obj(self):
        return _SensitiveDataFilter()

    def _make_record(self, msg: str) -> logging.LogRecord:
        """テスト用 LogRecord を作成"""
        return logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg=msg,
            args=(),
            exc_info=None,
        )

    def test_authorization_header_bearer(self, filter_obj):
        """Authorization: Bearer トークンがマスクされる"""
        record = self._make_record("Authorization: Bearer abcdef123456")
        filter_obj.filter(record)
        assert "abcd***" in record.msg
        assert "abcdef123456" not in record.msg

    def test_authorization_header_no_bearer(self, filter_obj):
        """Authorization: トークンがマスクされる (Bearer なし)"""
        record = self._make_record("Authorization: secretkey123")
        filter_obj.filter(record)
        assert "secr***" in record.msg
        assert "secretkey123" not in record.msg

    def test_x_api_key_header(self, filter_obj):
        """X-API-Key ヘッダーがマスクされる"""
        record = self._make_record("X-API-Key: myapikey123")
        filter_obj.filter(record)
        assert "myap***" in record.msg
        assert "myapikey123" not in record.msg

    def test_api_key_query_param(self, filter_obj):
        """api_key クエリパラメータがマスクされる"""
        record = self._make_record("GET /api?api_key=secretkey123")
        filter_obj.filter(record)
        assert "secr***" in record.msg
        assert "secretkey123" not in record.msg

    def test_access_token_query_param(self, filter_obj):
        """access_token クエリパラメータがマスクされる"""
        record = self._make_record("GET /api?access_token=token456")
        filter_obj.filter(record)
        assert "toke***" in record.msg
        assert "token456" not in record.msg

    def test_refresh_token_query_param(self, filter_obj):
        """refresh_token クエリパラメータがマスクされる"""
        record = self._make_record("POST /auth?refresh_token=refreshtoken123")
        filter_obj.filter(record)
        assert "refr***" in record.msg
        assert "refreshtoken123" not in record.msg

    def test_bearer_token_standalone(self, filter_obj):
        """単体の Bearer トークンがマスクされる"""
        record = self._make_record("Bearer secrettoken123")
        filter_obj.filter(record)
        assert "secr***" in record.msg
        assert "secrettoken123" not in record.msg

    def test_password_field(self, filter_obj):
        """password フィールドがマスクされる"""
        record = self._make_record("password=secretpass123")
        filter_obj.filter(record)
        assert "secr***" in record.msg
        assert "secretpass123" not in record.msg

    def test_client_secret_field(self, filter_obj):
        """client_secret フィールドがマスクされる"""
        record = self._make_record("client_secret=mysecret123")
        filter_obj.filter(record)
        assert "myse***" in record.msg
        assert "mysecret123" not in record.msg

    def test_private_key_field(self, filter_obj):
        """private_key フィールドがマスクされる"""
        record = self._make_record("private_key=myprivatekey123")
        filter_obj.filter(record)
        assert "mypr***" in record.msg
        assert "myprivatekey123" not in record.msg

    def test_refresh_token_field(self, filter_obj):
        """refresh_token フィールドがマスクされる"""
        record = self._make_record("refresh_token=refreshtoken123")
        filter_obj.filter(record)
        assert "refr***" in record.msg
        assert "refreshtoken123" not in record.msg

    def test_x_api_key_field(self, filter_obj):
        """X-API-Key フィールドがマスクされる"""
        record = self._make_record("X-API-Key: myapikey123")
        filter_obj.filter(record)
        assert "myap***" in record.msg
        assert "myapikey123" not in record.msg

    def test_args_masking(self, filter_obj):
        """args 属性の機密データもマスクされる"""
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="User login with token %s",
            args=("Bearer secrettoken123",),
            exc_info=None,
        )
        filter_obj.filter(record)
        assert "secr***" in record.args[0]
        assert "secrettoken123" not in record.args[0]

    def test_args_dict_masking(self, filter_obj):
        """args が辞書の場合もマスクされる"""
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="User data: %s",
            args={"api_key": "secretkey123", "name": "John"},
            exc_info=None,
        )
        filter_obj.filter(record)
        assert "secr***" in record.args["api_key"]
        assert "secretkey123" not in record.args["api_key"]
        assert record.args["name"] == "John"

    def test_non_string_msg_unchanged(self, filter_obj):
        """文字列以外の msg は変更されない"""
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg=12345,
            args=(),
            exc_info=None,
        )
        filter_obj.filter(record)
        assert record.msg == 12345


class TestConfigureIntegration:
    """configure() 関数の統合テスト"""

    def test_configure_runs_without_error(self):
        """configure() がエラーなく実行される"""
        configure()
        # 再実行してもエラーにならない
        configure()

    def test_configure_adds_sensitive_filter(self):
        """configure() がハンドラーに SensitiveDataFilter を登録する"""
        configure()
        root = logging.getLogger()
        # ハンドラーのフィルタに _SensitiveDataFilter が含まれている
        assert any(
            any(isinstance(f, _SensitiveDataFilter) for f in h.filters)
            for h in root.handlers
        )

    def test_logging_output_is_masked(self, caplog):
        """実際のログ出力がマスクされる"""
        # configure() は fixture 実行前に呼ばれるため、ここでは呼ばない
        logger = logging.getLogger("test.masking")
        logger.propagate = True

        with caplog.at_level(logging.INFO):
            logger.info("Authorization: Bearer abcdef123456")

        assert len(caplog.records) == 1
        assert "abcd***" in caplog.text
        assert "abcdef123456" not in caplog.text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])