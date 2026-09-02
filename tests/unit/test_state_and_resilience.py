"""Unit tests for src/services/state_manager.py, src/services/resilience.py, src/services/reproducibility.py."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
import hashlib

from src.services.state_manager import StateManager
from src.services.resilience import (
    is_offline_mode_enabled,
    check_database,
    check_gemini,
    get_system_status,
)
from src.services.reproducibility import (
    compute_input_hash,
    build_run_record,
    build_report,
)


class TestStateManager:
    """Tests for StateManager class."""

    def setup_method(self):
        self.mock_uow = AsyncMock()
        self.mock_uow.__aenter__ = AsyncMock(return_value=self.mock_uow)
        self.mock_uow.__aexit__ = AsyncMock(return_value=None)
        self.mock_uow.misc = AsyncMock()
        self.mock_uow.misc.save_internal_state = AsyncMock()
        self.mock_uow.misc.get_internal_state = AsyncMock()
        self.mock_uow.commit = AsyncMock()

        self.manager = StateManager(uow=self.mock_uow)

    @pytest.mark.asyncio
    async def test_save_state(self):
        """Test saving state."""
        await self.manager.save_state("test_key", {"data": "value"})

        self.mock_uow.misc.save_internal_state.assert_called_once_with("test_key", {"data": "value"})
        self.mock_uow.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_state(self):
        """Test getting state."""
        self.mock_uow.misc.get_internal_state.return_value = {"data": "value"}

        result = await self.manager.get_state("test_key")

        assert result == {"data": "value"}
        self.mock_uow.misc.get_internal_state.assert_called_once_with("test_key")


class TestResilience:
    """Tests for resilience module."""

    def test_is_offline_mode_enabled_false_by_default(self):
        """Test offline mode is disabled by default."""
        with patch.dict("os.environ", {}, clear=True):
            assert is_offline_mode_enabled() is False

    def test_is_offline_mode_enabled_true_values(self):
        """Test offline mode enabled for various true values."""
        for val in ["1", "true", "yes", "True", "YES"]:
            with patch.dict("os.environ", {"OFFLINE_MODE": val}):
                assert is_offline_mode_enabled() is True

    def test_is_offline_mode_enabled_false_values(self):
        """Test offline mode disabled for various false values."""
        for val in ["0", "false", "no", "False", "NO", ""]:
            with patch.dict("os.environ", {"OFFLINE_MODE": val}):
                assert is_offline_mode_enabled() is False

    @patch("src.services.resilience.AppContainer")
    @patch("asyncio.get_event_loop")
    def test_check_database_success(self, mock_loop, mock_container):
        """Test successful database check."""
        mock_engine = AsyncMock()
        mock_conn = AsyncMock()
        mock_engine.connect.return_value.__aenter__.return_value = mock_conn
        mock_container.db.return_value.engine = mock_engine
        mock_loop.return_value.run_until_complete = lambda coro: coro

        result = check_database()

        assert result == "ok"
        mock_conn.execute.assert_called_once()

    @patch("src.services.resilience.AppContainer")
    def test_check_database_failure(self, mock_container):
        """Test database check failure."""
        mock_container.db.side_effect = Exception("DB connection failed")

        result = check_database()

        assert result == "error"

    @patch("src.services.resilience.genai")
    def test_check_gemini_no_key(self, mock_genai):
        """Test Gemini check with no API key."""
        with patch.dict("os.environ", {"GEMINI_API_KEY": ""}):
            result = check_gemini()
            assert result == "disabled"

    @patch("src.services.resilience.genai")
    def test_check_gemini_success(self, mock_genai):
        """Test successful Gemini check."""
        mock_genai.list_models.return_value = [MagicMock(), MagicMock()]

        with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
            result = check_gemini()
            assert result == "ok"

    @patch("src.services.resilience.genai")
    def test_check_gemini_failure(self, mock_genai):
        """Test Gemini check failure."""
        mock_genai.configure.side_effect = Exception("API error")

        with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
            result = check_gemini()
            assert result == "error"

    @patch("src.services.resilience.check_database")
    @patch("src.services.resilience.check_gemini")
    @patch("src.services.resilience.is_offline_mode_enabled")
    def test_get_system_status_online(self, mock_offline, mock_gemini, mock_db):
        """Test system status when online."""
        mock_offline.return_value = False
        mock_db.return_value = "ok"
        mock_gemini.return_value = "ok"

        status = get_system_status()

        assert status["mode"] == "online"
        assert status["offline_mode_enabled"] is False
        assert status["database"] == "ok"
        assert status["gemini"] == "ok"
        assert status["cache_first"] is False
        assert "オンライン" in status["recommendation"]

    @patch("src.services.resilience.check_database")
    @patch("src.services.resilience.check_gemini")
    @patch("src.services.resilience.is_offline_mode_enabled")
    def test_get_system_status_offline_mode(self, mock_offline, mock_gemini, mock_db):
        """Test system status when offline mode enabled."""
        mock_offline.return_value = True
        mock_db.return_value = "ok"
        mock_gemini.return_value = "ok"

        status = get_system_status()

        assert status["mode"] == "offline"
        assert status["offline_mode_enabled"] is True
        assert status["cache_first"] is True
        assert "オフライン" in status["recommendation"]

    @patch("src.services.resilience.check_database")
    @patch("src.services.resilience.check_gemini")
    @patch("src.services.resilience.is_offline_mode_enabled")
    def test_get_system_status_degraded(self, mock_offline, mock_gemini, mock_db):
        """Test system status when degraded (Gemini error)."""
        mock_offline.return_value = False
        mock_db.return_value = "ok"
        mock_gemini.return_value = "error"

        status = get_system_status()

        assert status["mode"] == "degraded"
        assert status["offline_mode_enabled"] is False
        assert status["cache_first"] is True
        assert "オフライン" in status["recommendation"]


class TestReproducibility:
    """Tests for reproducibility module."""

    def test_compute_input_hash(self):
        """Test input hash computation."""
        payload = {"key1": "value1", "key2": 123, "key3": ["a", "b"]}
        hash1 = compute_input_hash(payload)
        hash2 = compute_input_hash(payload)
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex

    def test_compute_input_hash_deterministic(self):
        """Test hash is deterministic regardless of key order."""
        payload1 = {"a": 1, "b": 2}
        payload2 = {"b": 2, "a": 1}
        assert compute_input_hash(payload1) == compute_input_hash(payload2)

    def test_compute_input_hash_different(self):
        """Test different payloads produce different hashes."""
        hash1 = compute_input_hash({"key": "value1"})
        hash2 = compute_input_hash({"key": "value2"})
        assert hash1 != hash2

    def test_compute_input_hash_complex(self):
        """Test hash with complex nested structures."""
        payload = {
            "nested": {"a": 1, "b": [1, 2, 3]},
            "list": [{"x": 1}, {"y": 2}],
            "none": None,
        }
        hash_result = compute_input_hash(payload)
        assert len(hash_result) == 64

    def test_build_run_record(self):
        """Test building run record."""
        record = build_run_record(
            book_id=1,
            task_type="generation",
            prompt_version="v1.0",
            model_name="gemini-2.5-pro",
            params={"temp": 0.7},
            payload={"prompt": "test"},
            output_preview="Generated story...",
            trace_id="trace-123",
            chapter_ep=5,
        )

        assert record["book_id"] == 1
        assert record["task_type"] == "generation"
        assert record["prompt_version"] == "v1.0"
        assert record["model_name"] == "gemini-2.5-pro"
        assert record["params_json"] == '{"temp": 0.7}'
        assert record["input_hash"] == compute_input_hash({"prompt": "test"})
        assert record["output_preview"] == "Generated story..."
        assert record["trace_id"] == "trace-123"
        assert record["chapter_ep"] == 5

    def test_build_run_record_truncates_preview(self):
        """Test output preview is truncated."""
        long_preview = "x" * 1000
        record = build_run_record(
            book_id=1, task_type="test", prompt_version="v1", model_name="m",
            params={}, payload={}, output_preview=long_preview
        )
        assert len(record["output_preview"]) == 500

    def test_build_run_record_no_chapter(self):
        """Test build_run_record without chapter_ep."""
        record = build_run_record(
            book_id=1, task_type="test", prompt_version="v1", model_name="m",
            params={}, payload={}
        )
        assert record["chapter_ep"] is None

    def test_build_report(self):
        """Test building reproducibility report."""
        runs = [
            build_run_record(1, "gen", "v1", "m1", {}, {"p": "1"}, "out1", "t1", 1),
            build_run_record(1, "gen", "v1", "m1", {}, {"p": "2"}, "out2", "t2", 2),
        ]
        report = build_report(runs)

        assert report["count"] == 2
        assert report["runs"] == runs
        assert "# 生成再現性レポート" in report["markdown"]
        assert "記録数: 2" in report["markdown"]
        assert "タスク: gen (第1話)" in report["markdown"]
        assert "タスク: gen (第2話)" in report["markdown"]
        assert "Trace ID: `t1`" in report["markdown"]
        assert "Trace ID: `t2`" in report["markdown"]

    def test_build_report_empty(self):
        """Test building report with no runs."""
        report = build_report([])
        assert report["count"] == 0
        assert report["runs"] == []
        assert "記録数: 0" in report["markdown"]


class TestIntegration:
    """Integration tests across modules."""

    @pytest.mark.asyncio
    async def test_state_manager_with_reproducibility(self):
        """Test StateManager can store reproducibility records."""
        mock_uow = AsyncMock()
        mock_uow.__aenter__ = AsyncMock(return_value=mock_uow)
        mock_uow.__aexit__ = AsyncMock(return_value=None)
        mock_uow.misc = AsyncMock()
        mock_uow.misc.save_internal_state = AsyncMock()
        mock_uow.commit = AsyncMock()

        manager = StateManager(uow=mock_uow)

        record = build_run_record(
            book_id=1, task_type="generation", prompt_version="v1",
            model_name="gemini", params={}, payload={}, trace_id="trace-1"
        )

        await manager.save_state("run_record_1", record)

        mock_uow.misc.save_internal_state.assert_called_once_with("run_record_1", record)

    def test_resilience_offline_mode_affects_cache_strategy(self):
        """Test that offline mode affects cache-first strategy."""
        with patch("src.services.resilience.is_offline_mode_enabled", return_value=True):
            with patch("src.services.resilience.check_database", return_value="ok"):
                with patch("src.services.resilience.check_gemini", return_value="ok"):
                    status = get_system_status()
                    assert status["cache_first"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])