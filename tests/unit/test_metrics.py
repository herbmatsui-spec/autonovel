"""
tests/test_metrics.py - Prometheus メトリクスの単体テスト
"""

from unittest.mock import MagicMock

import pytest

from src.backend.observability.metrics import (
    MetricsMiddleware,
    PathNormalizer,
    chromadb_collections,
    db_pool_connections_active,
    db_pool_connections_idle,
    http_request_duration_seconds,
    http_requests_in_progress,
    http_requests_total,
    huey_queue_depth,
    huey_tasks_processed_total,
    llm_api_calls_total,
    llm_api_tokens_total,
    metrics_endpoint,
    novel_generation_duration_seconds,
    novel_generation_tasks_total,
    record_generation_task,
    record_http_metrics,
    record_huey_task,
    record_llm_call,
    redis_connected_clients,
    update_chromadb_collections,
    update_db_pool_metrics,
    update_huey_queue_depth,
    update_redis_clients,
)


class TestMetricsDefinitions:
    """メトリクス定義の存在確認"""

    def test_http_metrics_exist(self):
        assert http_requests_total is not None
        assert http_request_duration_seconds is not None
        assert http_requests_in_progress is not None

    def test_app_metrics_exist(self):
        assert novel_generation_tasks_total is not None
        assert novel_generation_duration_seconds is not None
        assert llm_api_calls_total is not None
        assert llm_api_tokens_total is not None
        assert db_pool_connections_active is not None
        assert db_pool_connections_idle is not None
        assert huey_queue_depth is not None
        assert huey_tasks_processed_total is not None
        assert chromadb_collections is not None
        assert redis_connected_clients is not None


class TestUtilityFunctions:
    """ユーティリティ関数のテスト"""

    def test_record_http_metrics(self):
        """HTTP メトリクス記録"""
        # カウンター初期値確認
        before = http_requests_total.labels(method="GET", path="/test", status="200")._value.get()

        record_http_metrics("GET", "/test", 200, 0.123)

        after = http_requests_total.labels(method="GET", path="/test", status="200")._value.get()
        assert after == before + 1

        # ヒストグラムも記録される（観測値の確認は内部実装依存のためスキップ）

    def test_record_generation_task(self):
        """生成タスクメトリクス記録"""
        before = novel_generation_tasks_total.labels(workflow_type="easy", status="started")._value.get()

        record_generation_task("easy", "started")

        after = novel_generation_tasks_total.labels(workflow_type="easy", status="started")._value.get()
        assert after == before + 1

        # duration 指定時
        record_generation_task("easy", "completed", 45.5)
        # ヒストグラム観測は内部確認が難しいためスキップ

    def test_record_llm_call(self):
        """LLM 呼び出しメトリクス記録"""
        before_calls = llm_api_calls_total.labels(model="test-model", status="success")._value.get()
        before_prompt = llm_api_tokens_total.labels(model="test-model", type="prompt")._value.get()
        before_completion = llm_api_tokens_total.labels(model="test-model", type="completion")._value.get()

        record_llm_call("test-model", "success", prompt_tokens=100, completion_tokens=50)

        after_calls = llm_api_calls_total.labels(model="test-model", status="success")._value.get()
        after_prompt = llm_api_tokens_total.labels(model="test-model", type="prompt")._value.get()
        after_completion = llm_api_tokens_total.labels(model="test-model", type="completion")._value.get()

        assert after_calls == before_calls + 1
        assert after_prompt == before_prompt + 100
        assert after_completion == before_completion + 50

    def test_update_db_pool_metrics(self):
        """DB プールメトリクス更新"""
        update_db_pool_metrics(3, 7)

        assert db_pool_connections_active._value.get() == 3
        assert db_pool_connections_idle._value.get() == 7

    def test_update_huey_queue_depth(self):
        """Huey キュー深度更新"""
        update_huey_queue_depth(15)

        assert huey_queue_depth._value.get() == 15

    def test_record_huey_task(self):
        """Huey タスク処理記録"""
        before = huey_tasks_processed_total.labels(status="success")._value.get()

        record_huey_task("success")

        after = huey_tasks_processed_total.labels(status="success")._value.get()
        assert after == before + 1

    def test_update_chromadb_collections(self):
        """ChromaDB コレクション数更新"""
        update_chromadb_collections(4)

        assert chromadb_collections._value.get() == 4

    def test_update_redis_clients(self):
        """Redis 接続クライアント数更新"""
        update_redis_clients(8)

        assert redis_connected_clients._value.get() == 8


class TestMetricsEndpoint:
    """metrics_endpoint 関数のテスト"""

    @pytest.mark.asyncio
    async def test_metrics_endpoint_returns_prometheus_format(self):
        """Prometheus 形式でレスポンスを返す"""
        response = await metrics_endpoint()

        assert "text/plain" in response.media_type
        assert "charset=utf-8" in response.media_type
        content = response.body.decode("utf-8")

        # 主要メトリクスが含まれることを確認
        assert "http_requests_total" in content
        assert "http_request_duration_seconds" in content
        assert "novel_generation_tasks_total" in content
        assert "llm_api_calls_total" in content
        assert "db_pool_connections_active" in content
        assert "huey_queue_depth" in content
        assert "chromadb_collections" in content
        assert "redis_connected_clients" in content


class TestPathNormalizer:
    """PathNormalizer のテスト"""

    def test_normalize_book_id(self):
        normalizer = PathNormalizer()
        assert normalizer.normalize("/api/books/123") == "/api/books/{id}"
        assert normalizer.normalize("/api/books/99999") == "/api/books/{id}"

    def test_normalize_episode_id(self):
        normalizer = PathNormalizer()
        assert normalizer.normalize("/api/episodes/456") == "/api/episodes/{id}"

    def test_normalize_task_id(self):
        normalizer = PathNormalizer()
        assert normalizer.normalize("/api/tasks/abc123") == "/api/tasks/{id}"
        assert normalizer.normalize("/api/tasks/xyz-789") == "/api/tasks/{id}"

    def test_normalize_plot_id(self):
        normalizer = PathNormalizer()
        assert normalizer.normalize("/api/plots/789") == "/api/plots/{id}"

    def test_normalize_chapter_id(self):
        normalizer = PathNormalizer()
        assert normalizer.normalize("/api/chapters/111") == "/api/chapters/{id}"

    def test_normalize_prompt_version_id(self):
        normalizer = PathNormalizer()
        assert normalizer.normalize("/api/prompt-versions/222") == "/api/prompt-versions/{id}"

    def test_normalize_unknown_path(self):
        normalizer = PathNormalizer()
        assert normalizer.normalize("/api/unknown") == "/api/unknown"
        assert normalizer.normalize("/health") == "/health"
        assert normalizer.normalize("/metrics") == "/metrics"


class TestMetricsMiddleware:
    """MetricsMiddleware のテスト"""

    @pytest.mark.asyncio
    async def test_middleware_records_metrics(self):
        """ミドルウェアがメトリクスを記録する"""
        middleware = MetricsMiddleware()

        # モックリクエスト・レスポンス
        mock_request = MagicMock()
        mock_request.method = "GET"
        mock_request.url.path = "/api/test"

        mock_response = MagicMock()
        mock_response.status_code = 200

        async def mock_call_next(request):
            return mock_response

        # 実行前のカウント
        before = http_requests_total.labels(method="GET", path="/api/test", status="200")._value.get()

        # ミドルウェア実行
        response = await middleware(mock_request, mock_call_next)

        # 実行後のカウント
        after = http_requests_total.labels(method="GET", path="/api/test", status="200")._value.get()

        assert response == mock_response
        assert after == before + 1

        # in_progress ゲージが元に戻っているか
        assert http_requests_in_progress.labels(method="GET", path="/api/test")._value.get() == 0

    @pytest.mark.asyncio
    async def test_middleware_records_error(self):
        """エラー時もメトリクスを記録する"""
        middleware = MetricsMiddleware()

        mock_request = MagicMock()
        mock_request.method = "POST"
        mock_request.url.path = "/api/error"

        async def mock_call_next(request):
            raise Exception("Internal error")

        before = http_requests_total.labels(method="POST", path="/api/error", status="500")._value.get()

        with pytest.raises(Exception):
            await middleware(mock_request, mock_call_next)

        after = http_requests_total.labels(method="POST", path="/api/error", status="500")._value.get()
        assert after == before + 1

        # in_progress ゲージが元に戻っているか
        assert http_requests_in_progress.labels(method="POST", path="/api/error")._value.get() == 0


class TestTrackLLMMetricsDecorator:
    """track_llm_metrics デコレータのテスト"""

    @pytest.mark.asyncio
    async def test_decorator_records_success(self):
        """成功時のメトリクス記録"""
        from src.backend.observability.metrics import track_llm_metrics

        @track_llm_metrics("test-model")
        async def mock_llm_call():
            return "result"

        before = llm_api_calls_total.labels(model="test-model", status="success")._value.get()

        result = await mock_llm_call()

        after = llm_api_calls_total.labels(model="test-model", status="success")._value.get()

        assert result == "result"
        assert after == before + 1

    @pytest.mark.asyncio
    async def test_decorator_records_error(self):
        """エラー時のメトリクス記録"""
        from src.backend.observability.metrics import track_llm_metrics

        @track_llm_metrics("test-model")
        async def mock_llm_call_error():
            raise Exception("LLM Error")

        before = llm_api_calls_total.labels(model="test-model", status="error")._value.get()

        with pytest.raises(Exception):
            await mock_llm_call_error()

        after = llm_api_calls_total.labels(model="test-model", status="error")._value.get()

        assert after == before + 1
