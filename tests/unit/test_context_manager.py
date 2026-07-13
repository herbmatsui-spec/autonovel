import pytest

from src.backend.engine_context import ContextManager
from src.models import PlotDbModel


class MockCharacterDbModel:
    def __init__(self, name, role="村人", registry_data=None):
        self.name = name
        self.role = role
        self.registry_data = registry_data or {}

class MockDataRepository:
    def __init__(self):
        self.books = {}
        self.plots = {}
        self.chapters = {}
        self.rag_ctx = ""

    async def get_book(self, book_id: int):
        class MockBook:
            current_branch_id = 1
        return MockBook()

    async def get_chapters_before(self, branch_id: int, ep_num: int):
        return []

    async def get_relevant_past_logs(self, branch_id: int, ep_num: int, query_text: str):
        return self.rag_ctx

@pytest.mark.asyncio
async def test_filter_active_characters():
    repo = MockDataRepository()
    ctx_mgr = ContextManager(repo)

    plots = [PlotDbModel(book_id=1, ep_num=1, detailed_blueprint="アリスとボブが出会う。")]
    chars = [
        MockCharacterDbModel("アリス", "主人公", {"personality": "元気", "ability": "炎"}),
        MockCharacterDbModel("ボブ", "村人"),
        MockCharacterDbModel("チャーリー", "村人") #登場しない
    ]
    char_states = {}

    res = ctx_mgr.filter_active_characters(plots, chars, char_states, recent_ctx="")

    assert "アリス" in res
    assert "ボブ" in res
    assert "チャーリー" not in res
