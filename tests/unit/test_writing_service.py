"""WritingService のユニットテスト。

対象: UltimateHegemonyEngine の肥大化解消に向けた WritingService 抽出 (Phase 4)。
WritingService は WritingAgent を内包し、generate_episodes_pipeline /
generate_episodes / analyze_and_import_chapter を委譲する。
"""
from typing import Any, List, Tuple

import pytest

from src.backend.protocols import WritingPort
from src.backend.writing_service import WritingService
from src.shared.utils import StatusReporter


class _FakeWriter:
    """WritingAgent のモック。"""

    def __init__(self) -> None:
        self.calls: list[tuple] = []
        self.has_import = True

    async def generate_episodes_pipeline(
        self, book_id, start_ep, end_ep, passion, target_word_count, is_easy_mode,
        reporter, branch_id=1, style_tag=None,
    ) -> Tuple[int, List[Any]]:
        self.calls.append(("generate_episodes_pipeline", book_id, start_ep, end_ep))
        return 100, [1, 2, 3]

    async def generate_episodes(
        self, book_id, start_ep, end_ep, passion, target_word_count, is_easy_mode,
        reporter, branch_id=1, style_tag=None,
    ) -> int:
        self.calls.append(("generate_episodes", book_id, start_ep, end_ep))
        return 50

    async def analyze_and_import_chapter(
        self, book_id, ep_num, import_text, do_refine=True,
    ) -> dict:
        self.calls.append(("analyze_and_import_chapter", book_id, ep_num))
        return {"status": "success"}


@pytest.fixture
def service() -> WritingService:
    writer = _FakeWriter()
    return WritingService(
        writer=writer,
        repo=object(),
        pm=object(),
        style_rag=object(),
        ctx_mgr=object(),
        reporter_factory=lambda: object(),
    )


@pytest.mark.asyncio
async def test_generate_episodes_pipeline_delegates(service: WritingService) -> None:
    chars, failed = await service.generate_episodes_pipeline(
        book_id=1, start_ep=1, end_ep=3, passion=0.6,
        target_word_count=2000, is_easy_mode=True, reporter=None,
    )
    assert chars == 100
    assert failed == [1, 2, 3]
    assert service.writer.calls[0][0] == "generate_episodes_pipeline"


@pytest.mark.asyncio
async def test_generate_episodes_delegates(service: WritingService) -> None:
    chars = await service.generate_episodes(
        book_id=1, start_ep=1, end_ep=3, passion=0.6,
        target_word_count=2000, is_easy_mode=True, reporter=None,
    )
    assert chars == 50
    assert service.writer.calls[-1][0] == "generate_episodes"


@pytest.mark.asyncio
async def test_analyze_and_import_chapter_delegates(service: WritingService) -> None:
    result = await service.analyze_and_import_chapter(
        book_id=1, ep_num=2, import_text="本文", do_refine=True,
    )
    assert result == {"status": "success"}
    assert service.writer.calls[-1][0] == "analyze_and_import_chapter"


def test_init_attributes(service: WritingService) -> None:
    assert service is not None
    assert hasattr(service, "writer")
    assert hasattr(service, "repo")
    assert hasattr(service, "pm")
    assert hasattr(service, "style_rag")
    assert hasattr(service, "ctx_mgr")
    assert hasattr(service, "reporter_factory")


def test_satisfies_protocol() -> None:
    # 構造的サブタイプ確認 (mypy は実行時チェックしないが、属性存在で担保)
    assert hasattr(WritingService, "generate_episodes_pipeline")
    assert hasattr(WritingService, "generate_episodes")
    assert hasattr(WritingService, "analyze_and_import_chapter")
