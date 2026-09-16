import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.services.audit_service import AuditService

@pytest.fixture
def mock_fast_screener():
    screener = MagicMock()
    screener.screen_plot = AsyncMock()
    return screener

@pytest.fixture
def mock_ability_checker():
    checker = MagicMock()
    checker.audit_ability_consistency = AsyncMock()
    return checker

@pytest.fixture
def mock_deai_auditor():
    auditor = MagicMock()
    auditor.audit = AsyncMock()
    return auditor

@pytest.fixture
def audit_service(mock_fast_screener, mock_ability_checker, mock_deai_auditor):
    # We need to patch the imports in the module to return our mocks
    with patch('src.services.audit_service.FastPlotScreener', return_value=mock_fast_screener), \
         patch('src.services.audit_service.AbilityConsistencyChecker', return_value=mock_ability_checker), \
         patch('src.services.audit_service.DeAIAuditor', return_value=mock_deai_auditor), \
         patch('src.services.audit_service.MAX_CONSECUTIVE_PEAK_EPISODES', 3):
        service = AuditService(llm=MagicMock(), prompt_manager=MagicMock())
        # Replace the internal mocks with our fixtures so we can assert on them
        service.fast_screener = mock_fast_screener
        service.ability_checker = mock_ability_checker
        service.deai_auditor = mock_deai_auditor
        return service

@pytest.mark.asyncio
async def test_screen_plot(audit_service, mock_fast_screener):
    mock_fast_screener.screen_plot.return_value = (True, "OK")
    result = await audit_service.screen_plot("blueprint")
    assert result == (True, "OK")
    mock_fast_screener.screen_plot.assert_awaited_once_with("blueprint")

@pytest.mark.asyncio
async def test_audit_ability(audit_service, mock_ability_checker):
    mock_ability_checker.audit_ability_consistency.return_value = (False, "reason", "settings")
    result = await audit_service.audit_ability("blueprint", "settings_json", "characters_json")
    assert result == (False, "reason", "settings")
    mock_ability_checker.audit_ability_consistency.assert_awaited_once_with(
        "blueprint", "settings_json", "characters_json"
    )

@pytest.mark.asyncio
async def test_audit_deai(audit_service, mock_deai_auditor):
    mock_deai_auditor.audit.return_value = (True, "OK")
    result = await audit_service.audit_deai("content")
    assert result == (True, "OK")
    mock_deai_auditor.audit.assert_awaited_once_with("content")

def test_get_erotic_advice(audit_service):
    # Patch MAX_CONSECUTIVE_PEAK_EPISODES to 3 for this test
    with patch('src.services.audit_service.MAX_CONSECUTIVE_PEAK_EPISODES', 3):
        # Case 1: enough consecutive peaks >=4
        intensities = [1,1,5,5,5]
        advice = audit_service.get_erotic_advice(intensities, current_ep=5, total_eps=10)
        assert any("連続するピークシーンが多すぎます" in a for a in advice)
        # Case 2: average > 3.5
        intensities = [4,4,4,4]  # average 4.0
        advice = audit_service.get_erotic_advice(intensities, current_ep=4, total_eps=4)
        assert any("全体の官能強度の平均が高めです" in a for a in advice)
        # Case 3: no advice
        intensities = [1,2,3]  # average 2.0, and last three not all >=4
        advice = audit_service.get_erotic_advice(intensities, current_ep=3, total_eps=3)
        assert advice == []
