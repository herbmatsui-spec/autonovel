"""Unit tests for src/core/state/ui_store.py - UI State Store."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from src.core.state.ui_store import UIStateStore


class TestUIStateStore:
    """Tests for UIStateStore class."""

    def setup_method(self):
        # Reset class state
        UIStateStore._subscribers = {}

        # Mock session manager
        self.mock_session = MagicMock()
        self.mock_session.runtime = MagicMock()
        self.mock_session.wizard = MagicMock()

        # Initialize runtime attributes
        self.mock_session.runtime.monitored_jobs = {}
        self.mock_session.runtime.active_job_ids = {}
        self.mock_session.runtime.poll_fail_count = {}
        self.mock_session.runtime.poll_skip_until = {}
        self.mock_session.runtime.save_status = {}
        self.mock_session.runtime.ui_processing_lock = False
        self.mock_session.runtime.toasted_notification_keys = []
        self.mock_session.runtime.rerun_count = 0
        self.mock_session.runtime.api_key_validation_state = "idle"
        self.mock_session.runtime.api_key_validation_key = ""
        self.mock_session.runtime.api_key_validation_error = ""
        self.mock_session.runtime.api_key_input = ""
        self.mock_session.runtime.easy_genre_key = ""

        # Mock SessionManager
        self.session_manager_patcher = patch("src.core.state.ui_store.SessionManager")
        self.mock_session_manager = self.session_manager_patcher.start()
        self.mock_session_manager.save_state = MagicMock()

        # Mock get_session
        self.get_session_patcher = patch("src.core.state.ui_store.get_session", return_value=self.mock_session)
        self.mock_get_session = self.get_session_patcher.start()

        # Mock streamlit
        self.st_patcher = patch("src.core.state.ui_store.st", MagicMock())
        self.mock_st = self.st_patcher.start()

    def teardown_method(self):
        self.session_manager_patcher.stop()
        self.get_session_patcher.stop()
        self.st_patcher.stop()

    def test_get(self):
        """Test get returns session."""
        result = UIStateStore.get()
        assert result == self.mock_session

    def test_get_runtime(self):
        """Test get_runtime returns runtime state."""
        result = UIStateStore.get_runtime()
        assert result == self.mock_session.runtime

    def test_update(self):
        """Test update calls update function and saves."""
        def update_func(state):
            state.runtime.test_attr = "test_value"

        UIStateStore.update(update_func, notify_keys=["test_attr"])

        assert self.mock_session.runtime.test_attr == "test_value"
        self.mock_session_manager.save_state.assert_called_once_with(self.mock_session)

    def test_update_runtime(self):
        """Test update_runtime sets attribute and saves."""
        UIStateStore.update_runtime("test_attr", "test_value")

        assert self.mock_session.runtime.test_attr == "test_value"
        self.mock_session_manager.save_state.assert_called_once()

    def test_update_runtime_invalid_attr(self):
        """Test update_runtime raises for invalid attribute."""
        with pytest.raises(AttributeError):
            UIStateStore.update_runtime("invalid_attr", "value")

    def test_persist(self):
        """Test persist saves state."""
        UIStateStore.persist()
        self.mock_session_manager.save_state.assert_called_once_with(self.mock_session)

    def test_subscribe_and_notify(self):
        """Test subscribe and notify callbacks."""
        callback = MagicMock()
        UIStateStore.subscribe("test_key", callback)

        UIStateStore._notify("test_key", "test_value")
        callback.assert_called_once_with("test_value")

    def test_notify_multiple_callbacks(self):
        """Test notify calls all callbacks."""
        callback1 = MagicMock()
        callback2 = MagicMock()
        UIStateStore.subscribe("test_key", callback1)
        UIStateStore.subscribe("test_key", callback2)

        UIStateStore._notify("test_key", "value")
        callback1.assert_called_once_with("value")
        callback2.assert_called_once_with("value")

    def test_notify_callback_exception(self):
        """Test notify handles callback exceptions."""
        callback = MagicMock(side_effect=Exception("callback error"))
        UIStateStore.subscribe("test_key", callback)

        # Should not raise
        UIStateStore._notify("test_key", "value")

    # Job Management Tests
    def test_get_monitored_jobs(self):
        """Test get_monitored_jobs."""
        self.mock_session.runtime.monitored_jobs = {"key": "job"}
        result = UIStateStore.get_monitored_jobs()
        assert result == {"key": "job"}

    def test_set_active_job(self):
        """Test set_active_job."""
        mock_job = MagicMock()
        mock_job.task_id = "task-123"

        UIStateStore.set_active_job(mock_job, "default")

        assert self.mock_session.runtime.active_job_ids["default"] == "task-123"
        assert self.mock_session.runtime.monitored_jobs["default"] == mock_job

    def test_set_active_job_none(self):
        """Test set_active_job with None clears job."""
        self.mock_session.runtime.monitored_jobs = {"default": "job"}
        self.mock_session.runtime.active_job_ids = {"default": "task-123"}

        UIStateStore.set_active_job(None, "default")

        assert self.mock_session.runtime.monitored_jobs["default"] is None
        assert self.mock_session.runtime.active_job_ids["default"] is None

    def test_clear_active_job(self):
        """Test clear_active_job."""
        self.mock_session.runtime.monitored_jobs = {"default": "job"}
        self.mock_session.runtime.active_job_ids = {"default": "task-123"}
        self.mock_session.runtime.poll_fail_count = {"default": 5}
        self.mock_session.runtime.poll_skip_until = {"default": 123.0}

        UIStateStore.clear_active_job("default")

        assert self.mock_session.runtime.monitored_jobs["default"] is None
        assert self.mock_session.runtime.active_job_ids["default"] is None
        assert self.mock_session.runtime.poll_fail_count["default"] == 0
        assert self.mock_session.runtime.poll_skip_until["default"] == 0.0

    def test_set_job_id(self):
        """Test set_job_id."""
        UIStateStore.set_job_id("run1", "task-123")
        assert self.mock_session.runtime.active_job_ids["run1"] == "task-123"

    def test_clear_job_id(self):
        """Test clear_job_id."""
        self.mock_session.runtime.active_job_ids = {"run1": "task-123"}
        UIStateStore.clear_job_id("run1")
        assert self.mock_session.runtime.active_job_ids["run1"] is None

    def test_set_processing_lock(self):
        """Test set_processing_lock."""
        UIStateStore.set_processing_lock(True)
        assert self.mock_session.runtime.ui_processing_lock is True

        UIStateStore.set_processing_lock(False)
        assert self.mock_session.runtime.ui_processing_lock is False

    def test_is_processing(self):
        """Test is_processing."""
        self.mock_session.runtime.ui_processing_lock = True
        assert UIStateStore.is_processing() is True

        self.mock_session.runtime.ui_processing_lock = False
        assert UIStateStore.is_processing() is False

    # Polling & Task Progress Tests
    def test_get_poll_fail_count(self):
        """Test get_poll_fail_count."""
        self.mock_session.runtime.poll_fail_count = {"run1": 3}
        assert UIStateStore.get_poll_fail_count("run1") == 3
        assert UIStateStore.get_poll_fail_count("run2") == 0  # default

    def test_increment_poll_fail_count(self):
        """Test increment_poll_fail_count."""
        UIStateStore.increment_poll_fail_count("run1")
        assert self.mock_session.runtime.poll_fail_count["run1"] == 1

        UIStateStore.increment_poll_fail_count("run1")
        assert self.mock_session.runtime.poll_fail_count["run1"] == 2

    def test_reset_poll_fail_count(self):
        """Test reset_poll_fail_count."""
        self.mock_session.runtime.poll_fail_count = {"run1": 5}
        UIStateStore.reset_poll_fail_count("run1")
        assert self.mock_session.runtime.poll_fail_count["run1"] == 0

    def test_get_poll_skip_until(self):
        """Test get_poll_skip_until."""
        self.mock_session.runtime.poll_skip_until = {"run1": 123.5}
        assert UIStateStore.get_poll_skip_until("run1") == 123.5
        assert UIStateStore.get_poll_skip_until("run2") == 0.0

    def test_set_poll_skip_until(self):
        """Test set_poll_skip_until."""
        UIStateStore.set_poll_skip_until("run1", 456.7)
        assert self.mock_session.runtime.poll_skip_until["run1"] == 456.7

    def test_set_get_save_status(self):
        """Test set_save_status and get_save_status."""
        UIStateStore.set_save_status(1, "saving")
        assert self.mock_session.runtime.save_status[1] == "saving"
        assert UIStateStore.get_save_status(1) == "saving"

        UIStateStore.set_save_status(1, "saved")
        assert UIStateStore.get_save_status(1) == "saved"

        # Default for non-existent
        assert UIStateStore.get_save_status(999) == "idle"

    # Wizard & Genre Settings Tests
    def test_set_wizard_step(self):
        """Test set_wizard_step."""
        UIStateStore.set_wizard_step(3)
        assert self.mock_session.wizard.step == 3

    def test_update_wizard_data(self):
        """Test update_wizard_data."""
        UIStateStore.update_wizard_data({"key": "value"})
        assert self.mock_session.wizard.data == {"key": "value"}

    def test_set_easy_genre(self):
        """Test set_easy_genre."""
        UIStateStore.set_easy_genre("fantasy")
        assert self.mock_session.runtime.easy_genre_key == "fantasy"

    # API Key Validation Tests
    def test_get_set_api_key_validation_state(self):
        """Test API key validation state."""
        assert UIStateStore.get_api_key_validation_state() == "idle"
        UIStateStore.set_api_key_validation_state("validating")
        assert UIStateStore.get_api_key_validation_state() == "validating"

    def test_get_set_api_key_validation_key(self):
        """Test API key validation key."""
        assert UIStateStore.get_api_key_validation_key() == ""
        UIStateStore.set_api_key_validation_key("test-key")
        assert UIStateStore.get_api_key_validation_key() == "test-key"

    def test_get_set_api_key_validation_error(self):
        """Test API key validation error."""
        assert UIStateStore.get_api_key_validation_error() == ""
        UIStateStore.set_api_key_validation_error("Invalid key")
        assert UIStateStore.get_api_key_validation_error() == "Invalid key"

    def test_reset_api_key_validation(self):
        """Test reset_api_key_validation."""
        UIStateStore.set_api_key_validation_state("error")
        UIStateStore.set_api_key_validation_error("Invalid")
        UIStateStore.reset_api_key_validation()
        assert UIStateStore.get_api_key_validation_state() == "idle"
        assert UIStateStore.get_api_key_validation_error() == ""

    # Toast Notification Tests
    def test_is_toast_notified(self):
        """Test is_toast_notified."""
        self.mock_session.runtime.toasted_notification_keys = ["key1"]
        assert UIStateStore.is_toast_notified("key1") is True
        assert UIStateStore.is_toast_notified("key2") is False

    def test_mark_toast_notified(self):
        """Test mark_toast_notified."""
        UIStateStore.mark_toast_notified("key1")
        assert "key1" in self.mock_session.runtime.toasted_notification_keys

        # Duplicate should not add twice
        UIStateStore.mark_toast_notified("key1")
        assert self.mock_session.runtime.toasted_notification_keys.count("key1") == 1

    def test_clear_toast_notified(self):
        """Test clear_toast_notified."""
        self.mock_session.runtime.toasted_notification_keys = ["key1", "key2"]
        UIStateStore.clear_toast_notified("key1")
        assert "key1" not in self.mock_session.runtime.toasted_notification_keys
        assert "key2" in self.mock_session.runtime.toasted_notification_keys

    def test_toast_notify(self):
        """Test toast_notify calls st.toast."""
        UIStateStore.toast_notify("key1", "Test message", "✅")
        self.mock_st.toast.assert_called_once_with("Test message", icon="✅")
        assert "key1" in self.mock_session.runtime.toasted_notification_keys

    def test_toast_notify_already_notified(self):
        """Test toast_notify doesn't repeat."""
        self.mock_session.runtime.toasted_notification_keys = ["key1"]
        UIStateStore.toast_notify("key1", "Test message")
        self.mock_st.toast.assert_not_called()

    # Rerun & Utility Tests
    def test_get_rerun_count(self):
        """Test get_rerun_count."""
        self.mock_session.runtime.rerun_count = 5
        assert UIStateStore.get_rerun_count() == 5

    def test_increment_rerun_count(self):
        """Test increment_rerun_count."""
        self.mock_session.runtime.rerun_count = 0
        UIStateStore.increment_rerun_count()
        assert self.mock_session.runtime.rerun_count == 1

    def test_get_set_api_key_input(self):
        """Test API key input."""
        assert UIStateStore.get_api_key_input() == ""
        UIStateStore.set_api_key_input("test-key")
        assert UIStateStore.get_api_key_input() == "test-key"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])