"""
Test file for foreshadowing scope
PLAN 01: 伏線スコープのテスト
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.models.foreshadowing_status import ForeshadowingScope


class TestForeshadowingScope:
    """伏線スコープのテスト"""

    def test_short_term_scope(self):
        """短期伏線スコープのテスト"""
        assert ForeshadowingScope.SHORT_TERM.value == "short_term"

    def test_long_term_scope(self):
        """長期伏線スコープのテスト"""
        assert ForeshadowingScope.LONG_TERM.value == "long_term"

    def test_scope_values(self):
        """スコープ値のテスト"""
        scopes = [s.value for s in ForeshadowingScope]
        assert "short_term" in scopes
        assert "long_term" in scopes