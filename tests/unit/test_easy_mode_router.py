"""Tests for src.backend.routers.easy_mode router functions."""

import asyncio
from unittest.mock import MagicMock

import pytest

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
    class DummyGachaService:
        async def generate_plans(self, req):
            return {
                "request_id": "req-123",
                "plans": [
                    {"plan_id": "p1", "plan_type": "royal", "title": "王道", "logline": "...", "protagonist_summary": "...", "charm_point": "..."},
                ]
            }

    monkeypatch.setattr(easy_mode, "GachaService", DummyGachaService)
    class DummyDBManager:
        def get_session(self):
            class Session:
                async def __aenter__(self): return self
                async def __aexit__(self, *args): pass
            return Session()
    
    monkeypatch.setattr(easy_mode, "get_db_manager", lambda: DummyDBManager())
    
    req = easy_mode.GachaRequest(genre="fantasy", keywords=["magic"])
    response = await easy_mode.gacha_endpoint(req)
    assert response.request_id == "req-123"
    assert len(response.plans) == 1

@pytest.mark.asyncio
async def test_digest_endpoint(monkeypatch, dummy_request):
    class DummyDigestService:
        async def create_digest(self, req):
            return easy_mode.DigestResponse(
                book_id="book-123",
                title="Test Title",
                synopsis="Synopsis",
                episode_1_text="Ep1",
                climax_preview_text="Climax",
                status="completed"
            )

    monkeypatch.setattr(easy_mode, "DigestService", DummyDigestService)
    class DummyDBManager:
        def get_session(self):
            class Session:
                async def __aenter__(self): return self
                async def __aexit__(self, *args): pass
            return Session()
    
    monkeypatch.setattr(easy_mode, "get_db_manager", lambda: DummyDBManager())
    
    req = easy_mode.DigestRequest(request_id="req-123", selected_plan_id="p1")
    response = await easy_mode.digest_endpoint(req)
    assert response.book_id == "book-123"
    assert response.status == "completed"

@pytest.mark.asyncio
async def test_promote_endpoint(monkeypatch, dummy_request):
    class DummyPromotionService:
        async def promote_book(self, req):
            return easy_mode.PromotionResponse(
                success=True,
                redirect_url="/studio/book/1",
                state_token="token-123"
            )

    monkeypatch.setattr(easy_mode, "PromotionService", DummyPromotionService)
    class DummyDBManager:
        def get_session(self):
            class Session:
                async def __aenter__(self): return self
                async def __aexit__(self, *args): pass
            return Session()
    
    monkeypatch.setattr(easy_mode, "get_db_manager", lambda: DummyDBManager())
    
    req = easy_mode.PromotionRequest(book_id="1")
    response = await easy_mode.promote_endpoint(req)
    assert response.success is True
    assert response.state_token == "token-123"

@pytest.mark.asyncio
async def test_reverse_generate_endpoint(monkeypatch, dummy_request):
    class DummyWorkflow:
        async def execute(self, **kwargs):
            return {"status": "success", "plot": "Generated Plot"}
    
    monkeypatch.setattr(easy_mode, "ReversePlotGenerationWorkflow", DummyWorkflow)
    
    req = easy_mode.ReversePlotGeneratePayload(
        answers={"q1": "a1"},
        target_episodes=10,
        genre="fantasy",
        llm_config={}
    )
    response = await easy_mode.reverse_generate_endpoint(req)
    assert response["status"] == "success"
    assert "Generated Plot" in response["plot"]

@pytest.mark.asyncio
async def test_export_with_data_endpoint(monkeypatch, dummy_session):
    class DummyMarketingAgent:
        async def create_export_package(self, book_id, book_data=None):
            return b"ZIPDATA", "book_1.zip"
    
    monkeypatch.setattr(easy_mode, "MarketingAgent", DummyMarketingAgent)
    
    payload = easy_mode.ExportRequestPayload(
        title="Test Book",
        genre="fantasy",
        current_text="Content",
        character={"name": "Hero"},
        plots=[]
    )
    
    response = asyncio.run(
        easy_mode.export_with_data_endpoint(payload=payload, book_id=1, session=dummy_session)
    )
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/zip"

