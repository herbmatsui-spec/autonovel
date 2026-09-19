from pathlib import Path
from unittest.mock import AsyncMock, Mock
import jinja2
import pytest

from src.models.foreshadowing_status import ForeshadowingStatus
from src.services.foreshadowing_service import ForeshadowingService


def create_mock_repo():
    repo = Mock()
    f1 = Mock()
    f1.id = 10
    f1.book_id = 1
    f1.title = "謎の刺客の紋章"
    f1.description = "黒い鷲の紋章"
    f1.planted_episode = 3
    f1.target_episode = 12
    f1.scope = "short_term"
    f1.status = ForeshadowingStatus.PLANTED.value

    f2 = Mock()
    f2.id = 11
    f2.book_id = 1
    f2.title = "すでに回収済みの伏線"
    f2.description = "古い鍵"
    f2.planted_episode = 1
    f2.target_episode = 5
    f2.scope = "short_term"
    f2.status = ForeshadowingStatus.RESOLVED.value

    repo.get_by_ids = AsyncMock(return_value=[f1, f2])
    repo.get_unresolved = AsyncMock(return_value=[f1])
    return repo


@pytest.fixture
def mock_repo():
    return create_mock_repo()


@pytest.mark.asyncio
async def test_get_contract_foreshadowings_with_ids(mock_repo):
    """target_idsを指定した場合、未回収伏線のみが契約リストとして返ること"""
    service = ForeshadowingService(repo=mock_repo)
    contracts = await service.get_contract_foreshadowings(
        book_id=1,
        episode_num=12,
        target_ids=[10, 11],
    )
    # f2はRESOLVED済みなので弾かれ、f1（ID=10）のみが返る
    assert len(contracts) == 1
    assert contracts[0]["id"] == 10
    assert contracts[0]["title"] == "謎の刺客の紋章"


@pytest.mark.asyncio
async def test_contract_prompt_rendering(mock_repo):
    """取得した契約伏線がJinja2テンプレートに正しくレンダリングされること"""
    service = ForeshadowingService(repo=mock_repo)
    contracts = await service.get_contract_foreshadowings(
        book_id=1,
        episode_num=12,
        target_ids=[10],
    )

    template_path = Path("prompts/templates/narrative/foreshadowing_contract_instruction.j2")
    template = jinja2.Template(template_path.read_text(encoding="utf-8"))

    rendered = template.render(
        contract_foreshadowings=contracts,
        background_foreshadowings=[],
    )

    assert "本話の絶対回収ミッション（契約伏線）" in rendered
    assert "謎の刺客の紋章" in rendered
    assert "黒い鷲の紋章" in rendered
    assert "resolved_foreshadowing_ids" in rendered
