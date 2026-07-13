import pytest
from pydantic import ValidationError

from schemas.app_state import AppRuntimeState, AppStateModel, TokenStats, WizardState


def test_runtime_state_defaults():
    """ランタイム状態のデフォルト値が正しく設定されているか検証"""
    state = AppRuntimeState()
    assert state.app_mode == "easy"
    assert state.is_api_key_valid is False
    assert state.active_job_id is None
    assert state.backend_connection_error is False

def test_runtime_state_validation():
    """不正な型が渡された場合にバリデーションエラーが発生するか検証"""
    with pytest.raises(ValidationError):
        # app_mode は str である必要があるが、リストを渡す
        AppRuntimeState(app_mode=["easy"])

def test_wizard_state_defaults():
    """ウィザード状態のデフォルト値が正しく設定されているか検証"""
    wizard = WizardState()
    assert wizard.step == 1
    assert wizard.data == {}

def test_app_state_model_composition():
    """AppStateModel が正しく他のモデルを内包しているか検証"""
    state = AppStateModel()
    assert isinstance(state.runtime, AppRuntimeState)
    assert isinstance(state.wizard, WizardState)
    assert state.current_book_id is None

def test_token_stats_validation():
    """TokenStats のバリデーションを検証"""
    stats = TokenStats(prompt_tokens=100, completion_tokens=200)
    assert stats.total_tokens == 300

    with pytest.raises(ValidationError):
        # 負の値は許容されない（正の整数であるべき）
        TokenStats(prompt_tokens=-1)
