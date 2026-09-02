"""`feature_flags` ユーティリティの単体テスト。"""
from __future__ import annotations

import pytest

from src.backend import config
from src.backend.exceptions import MultimediaDisabledError
from src.backend.feature_flags import (
    is_audio_synth_enabled,
    is_multimedia_enabled,
    require_audio_synth,
    require_multimedia,
)


def test_multimedia_disabled_by_default(monkeypatch):
    monkeypatch.setattr(config.settings, "ENABLE_MULTIMEDIA", False)
    assert is_multimedia_enabled() is False


def test_multimedia_enabled(monkeypatch):
    monkeypatch.setattr(config.settings, "ENABLE_MULTIMEDIA", True)
    assert is_multimedia_enabled() is True


def test_require_multimedia_raises_when_disabled(monkeypatch):
    monkeypatch.setattr(config.settings, "ENABLE_MULTIMEDIA", False)
    with pytest.raises(MultimediaDisabledError):
        require_multimedia()


def test_require_multimedia_passes_when_enabled(monkeypatch):
    monkeypatch.setattr(config.settings, "ENABLE_MULTIMEDIA", True)
    require_multimedia()


def test_audio_synth_flag(monkeypatch):
    monkeypatch.setattr(config.settings, "ENABLE_AUDIO_SYNTH", False)
    assert is_audio_synth_enabled() is False
    with pytest.raises(MultimediaDisabledError):
        require_audio_synth()
    monkeypatch.setattr(config.settings, "ENABLE_AUDIO_SYNTH", True)
    assert is_audio_synth_enabled() is True
    require_audio_synth()
