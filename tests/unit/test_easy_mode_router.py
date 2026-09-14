"""Tests for src.backend.routers.easy_mode router functions."""

import asyncio
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

import src.backend.tasks.huey as huey_mod
from src.backend.routers import easy_mode


class DummySession:
    """Minimal dummy session object for repository usage."""

    def __init__(self):
        self.added = []
        self.committed = False
        self.refreshed = None

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.committed = True

    def refresh(self, obj):
        self.refreshed = obj

    def get(self, model, id):
        return None


class DummyTask:

    def __init__(self, id):
        self.id = id


class DummyRepo:

    def __init__(self, session):
        self.session = session
        self.task_id = 42

    def create_task(self, task_id: str | None = None, status: str = "pending", result: str | None = None):
        return DummyTask(task_id or self.task_id)

    def update_task_status(self, task_id: str, status: str):
        pass

    def get_latest_bible(self, book_id: int):
        return None

    def get_all_non_anchor_chapters(self, *args, **kwargs):
        return []

    def get_all_characters(self, *args, **kwargs):
        return []

    def get_all_plots(self, *args, **kwargs):
        return []

    def get_book(self, *args, **kwargs):
        return None


@pytest.fixture
def dummy_session():
    return DummySession()


@pytest.fixture
def dummy_request():
    req = MagicMock()
    req.client.host = "127.0.0.1"
    return req


def patch_dependencies(monkeypatch):
    monkeypatch.setattr(easy_mode, "process_chapter", lambda x: f"processed:{x}")
    monkeypatch.setattr(easy_mode, "BookRepository", DummyRepo)

    # Mock generate_chapter_task
    class DummyTaskResult:
        def __init__(self):
            self.id = "test-huey-id"

    import src.backend.tasks.generation_tasks as gen_tasks_mod
    monkeypatch.setattr(gen_tasks_mod, "generate_chapter_task", lambda *args, **kwargs: DummyTaskResult())

    called = []

    class DummyMetrics:

        @staticmethod
        def increment(name):
            called.append(name)

    monkeypatch.setattr(easy_mode, "metrics", DummyMetrics)
    return called


@pytest.mark.asyncio
async def test_execute_generation(monkeypatch):
    from src.services.llm.mock_adapter import MockLLMAdapter
    monkeypatch.setattr(easy_mode, "get_llm_adapter", lambda **kwargs: MockLLMAdapter())
    payload = {
        "current_chapter": "テスト冒頭",
        "chapter_history": ["前話"],
        "character": {"name": "テスト勇者", "genre": "ファンタジー (R15)"},
    }
    result = await easy_mode.execute_generation(payload)
    assert "output" in result
    assert "suggestions" in result
    assert isinstance(result["suggestions"], list)


@pytest.mark.asyncio
async def test_generate_content_success(monkeypatch, dummy_session, dummy_request):
    called_metrics = patch_dependencies(monkeypatch)
    # orchestrated タスクをモック (実装は generate_chapter_orchestrated_task を利用)
    import src.backend.tasks.generation_tasks as gen_tasks_mod

    class DummyTaskResult:
        def __init__(self):
            self.id = "test-huey-id"

    monkeypatch.setattr(
        gen_tasks_mod,
        "generate_chapter_orchestrated_task",
        lambda *args, **kwargs: DummyTaskResult(),
    )
    valid_input = easy_mode.EasyModeInput(
        chapter_history=["prev chapter"],
        current_chapter="current content",
        character_params={"name": "hero"},
        content_length_limit=1000,
    )
    response = await easy_mode.generate_content(
        valid_input, request=dummy_request, session=dummy_session
    )
    assert isinstance(response, easy_mode.GenerationResponse)
    # huey_task_id should be in suggestions (now using huey enqueue)
    assert "test-huey-id" in response.suggestions[0]
    assert "tasks_enqueued" in called_metrics

@pytest.mark.asyncio
async def test_generate_content_stream(monkeypatch, dummy_session, dummy_request):
    """StreamQueryInput を含むストリーミング用モデルの存在と動作を検証する。

    実装上、ストリーミングは GET /easy_mode/generate/stream エンドポイント (SSE) で
    フロントエンドと連携するため、ここではクエリ互換入力の変換ロジックを検証する。
    """
    from src.domain.entities.easy_mode import StreamQueryInput

    # StreamQueryInput が EasyModeInput に正しく変換されることを確認
    query = StreamQueryInput(
        current_chapter="content",
        character_name="hero",
        content_length_limit=1000,
    )
    converted = query.to_easy_mode_input()
    assert converted.current_chapter == "content"
    assert converted.content_length_limit == 1000
    assert converted.character_params.name == "hero"


@pytest.mark.asyncio
async def test_generate_content_validation_error_path(
    monkeypatch, dummy_session, dummy_request
):
    class DummyValidationError(Exception):

        def errors(self):
            return [{"loc": "field", "msg": "msg", "type": "type"}]

    monkeypatch.setattr(easy_mode, "ValidationError", DummyValidationError)

    def raise_val_err(x):
        raise DummyValidationError()

    monkeypatch.setattr(easy_mode, "process_chapter", raise_val_err)
    valid_input = easy_mode.EasyModeInput(
        chapter_history=["a"],
        current_chapter="content",
        character_params={},
        content_length_limit=1000,
    )
    from src.backend.exceptions import ValidationException

    with pytest.raises(ValidationException):
        await easy_mode.generate_content(
            valid_input, request=dummy_request, session=dummy_session
        )


@pytest.mark.asyncio
async def test_generate_content_service_exception(
    monkeypatch, dummy_session, dummy_request
):
    def raise_runtime(x):
        raise RuntimeError("boom")

    monkeypatch.setattr(easy_mode, "process_chapter", raise_runtime)
    valid_input = easy_mode.EasyModeInput(
        chapter_history=["a"],
        current_chapter="content",
        character_params={},
        content_length_limit=1000,
    )
    from src.backend.exceptions import ServiceException

    with pytest.raises(ServiceException):
        await easy_mode.generate_content(
            valid_input, request=dummy_request, session=dummy_session
        )


class DummyMarketingAgent:

    def __init__(self, repo):
        self.repo = repo

    async def create_export_package(self, book_id: int):
        return b"ZIPDATA", f"book_{book_id}.zip"


def test_export_easy_mode_package(monkeypatch, dummy_session):
    monkeypatch.setattr(easy_mode, "MarketingAgent", DummyMarketingAgent)
    called = []

    class DummyMetrics:

        @staticmethod
        def increment(name):
            called.append(name)

    monkeypatch.setattr(easy_mode, "metrics", DummyMetrics)
    response = asyncio.run(
        easy_mode.export_easy_mode_package(book_id=1, session=dummy_session)
    )
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/zip"
    assert "attachment;" in response.headers["Content-Disposition"]
    assert "book_1.zip" in response.headers["Content-Disposition"]
    assert "exports_attempted" in called
    assert "exports_succeeded" in called


def test_get_task_status_pending(monkeypatch):
    monkeypatch.setattr(huey_mod, "result", lambda task_id: None)
    result = asyncio.run(easy_mode.get_task_status("abc123"))
    assert result["status"] == "pending"
    assert result["task_id"] == "abc123"


def test_get_task_status_completed(monkeypatch):
    monkeypatch.setattr(huey_mod, "result", lambda task_id: {"output": "done"})
    result = asyncio.run(easy_mode.get_task_status("xyz789"))
    assert result["status"] == "completed"
    assert result["result"] == {"output": "done"}
    assert result["task_id"] == "xyz789"


def test_get_task_status_failed(monkeypatch):
    monkeypatch.setattr(huey_mod, "result", lambda task_id: {"error": "LLM generation timeout", "text": "", "time": 0})
    result = asyncio.run(easy_mode.get_task_status("err456"))
    assert result["status"] == "failed"
    assert result["error"] == "LLM generation timeout"
    assert result["task_id"] == "err456"

@pytest.mark.asyncio
async def test_gacha_endpoint(monkeypatch, dummy_request):
    # 遅延 import される src.backend.database.core.get_db_manager をパッチ
    import src.backend.database.core as db_core
    from src.domain.entities.easy_mode import GachaPlan, GachaResponse

    class DummyGachaService:
        def __init__(self, db=None):
            self.db = db

        async def generate_plans(self, req):
            return GachaResponse(
                request_id="req-123",
                plans=[
                    GachaPlan(
                        plan_id="p1",
                        plan_type="royal",
                        title="王道",
                        logline="...",
                        protagonist_summary="...",
                        charm_point="...",
                    ),
                    GachaPlan(
                        plan_id="p2",
                        plan_type="curveball",
                        title="変化球",
                        logline="...",
                        protagonist_summary="...",
                        charm_point="...",
                    ),
                    GachaPlan(
                        plan_id="p3",
                        plan_type="dark",
                        title="ダーク",
                        logline="...",
                        protagonist_summary="...",
                        charm_point="...",
                    ),
                ],
            )

    class DummyDBManager:
        def get_session(self):
            class Session:
                async def __aenter__(self):
                    return self

                async def __aexit__(self, *args):
                    pass

            return Session()

    monkeypatch.setattr(db_core, "get_db_manager", lambda: DummyDBManager())
    monkeypatch.setattr(easy_mode, "GachaService", DummyGachaService)

    req = easy_mode.GachaRequest(genre="fantasy", keywords=["magic"])
    response = await easy_mode.gacha_endpoint(req)
    assert response.request_id == "req-123"
    assert len(response.plans) == 3

@pytest.mark.asyncio
async def test_digest_endpoint(monkeypatch, dummy_request):
    # 遅延 import される src.backend.database.core.get_db_manager をパッチ
    import src.backend.database.core as db_core

    class DummyDigestService:
        def __init__(self, db=None):
            self.db = db

        async def create_digest(self, req):
            return easy_mode.DigestResponse(
                book_id="book-123",
                title="Test Title",
                synopsis="Synopsis",
                episode_1_text="Ep1",
                climax_preview_text="Climax",
                status="completed",
            )

    class DummyDBManager:
        def get_session(self):
            class Session:
                async def __aenter__(self):
                    return self

                async def __aexit__(self, *args):
                    pass

            return Session()

    monkeypatch.setattr(db_core, "get_db_manager", lambda: DummyDBManager())
    monkeypatch.setattr(easy_mode, "DigestService", DummyDigestService)

    req = easy_mode.DigestRequest(request_id="req-123", selected_plan_id="p1")
    response = await easy_mode.digest_endpoint(req)
    assert response.book_id == "book-123"
    assert response.status == "completed"

@pytest.mark.asyncio
async def test_promote_endpoint(monkeypatch, dummy_request):
    # 遅延 import される src.backend.database.core.get_db_manager をパッチ
    import src.backend.database.core as db_core

    class DummyPromotionService:
        def __init__(self, db=None):
            self.db = db

        async def promote_book(self, req):
            return easy_mode.PromotionResponse(
                success=True,
                redirect_url="/studio/book/1",
                state_token="token-123",
            )

    class DummyDBManager:
        def get_session(self):
            class Session:
                async def __aenter__(self):
                    return self

                async def __aexit__(self, *args):
                    pass

            return Session()

    monkeypatch.setattr(db_core, "get_db_manager", lambda: DummyDBManager())
    monkeypatch.setattr(easy_mode, "PromotionService", DummyPromotionService)

    req = easy_mode.PromotionRequest(book_id="1")
    response = await easy_mode.promote_endpoint(req)
    assert response.success is True
    assert response.state_token == "token-123"

@pytest.mark.asyncio
async def test_reverse_generate_endpoint(monkeypatch, dummy_request):
    # 遅延 import される src.backend.workflows.reverse_plot_workflow をパッチ
    import src.backend.workflows.reverse_plot_workflow as wf_mod

    class DummyWorkflow:
        async def execute(self, **kwargs):
            return {"status": "success", "plot": "Generated Plot"}

    monkeypatch.setattr(wf_mod, "ReversePlotGenerationWorkflow", DummyWorkflow)

    req = easy_mode.ReversePlotGeneratePayload(
        answers={"q1": "a1"},
        target_episodes=10,
        genre="fantasy",
        llm_config={},
    )
    response = await easy_mode.reverse_generate_endpoint(req)
    assert response["status"] == "success"
    assert "Generated Plot" in response["plot"]

@pytest.mark.asyncio
async def test_export_with_data_endpoint(monkeypatch, dummy_session):
    class DummyMarketingAgent:
        def __init__(self, repo=None):
            self.repo = repo

        async def create_export_package(self, book_id, book_data=None):
            return b"ZIPDATA", "book_1.zip"

    monkeypatch.setattr(easy_mode, "MarketingAgent", DummyMarketingAgent)

    payload = easy_mode.ExportRequestPayload(
        title="Test Book",
        genre="fantasy",
        current_text="Content",
        character={"name": "Hero"},
        plots=[],
    )

    # pytest-asyncio のイベントループ内で直接 await する
    response = await easy_mode.export_with_data_endpoint(
        payload=payload, book_id=1, session=dummy_session
    )
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/zip"

@pytest.mark.asyncio
async def test_cancel_task(monkeypatch):
    class DummyRepo:
        def update_task_status(self, task_id, status):
            pass
    
    monkeypatch.setattr(easy_mode, "BookRepository", DummyRepo)
    monkeypatch.setattr(huey_mod, "revoke_by_id", lambda tid: None)
    
    response = await easy_mode.cancel_task("task-123")
    assert response["task_id"] == "task-123"
    assert response["status"] == "cancelled"

@pytest.mark.asyncio
async def test_generate_content_validation_error(monkeypatch, dummy_session, dummy_request):
    """EasyModeInput の Pydantic バリデーションが不正な入力を拒否することを確認する。

    chapter_history は list 型であるべき。文字列を渡すと Pydantic ValidationError が発生する。
    """
    from pydantic import ValidationError as PydanticValidationError

    # Provide invalid input: chapter_history should be list, not string
    with pytest.raises(PydanticValidationError) as exc_info:
        easy_mode.EasyModeInput(
            chapter_history="not a list",  # Should be list
            current_chapter="content",
            character_params={"name": "hero"},
            content_length_limit=1000,
        )

    # chapter_history フィールドに対するバリデーションエラーであることを確認
    errors = exc_info.value.errors()
    assert any(e["loc"] == ("chapter_history",) for e in errors)
    assert any(e["type"] == "list_type" for e in errors)

