"""
Regression test for Step 15: Monitoring initialization optimization in test environment.
Verifies that:
1. init_sentry() skips SDK initialization when running under pytest / TESTING=True.
2. init_otel() skips OpenTelemetry initialization when running under pytest / TESTING=True.
3. Under normal environment, init_sentry calls sentry_sdk.init if DSN is provided.
"""

import os
import time
from unittest.mock import patch, MagicMock
from src.monitoring.sentry import init_sentry
from src.monitoring.otel import init_otel


def test_monitoring_skips_in_pytest_environment():
    # Under pytest, PYTEST_CURRENT_TEST is naturally present in os.environ
    t0 = time.perf_counter()
    res_sentry = init_sentry()
    res_otel = init_otel()
    elapsed = time.perf_counter() - t0

    assert res_sentry is None
    assert res_otel is None
    # Must be virtually instantaneous (less than 50ms)
    assert elapsed < 0.05


def test_sentry_initializes_when_not_in_test_env():
    # Simulate production environment by removing test env vars temporarily
    env_backup = {k: os.environ.get(k) for k in ["PYTEST_CURRENT_TEST", "TESTING", "SENTRY_DSN"]}
    try:
        os.environ.pop("PYTEST_CURRENT_TEST", None)
        os.environ.pop("TESTING", None)
        os.environ["SENTRY_DSN"] = "https://fake_key@fake_host/123"

        with patch("sentry_sdk.init") as mock_sentry_init:
            app = MagicMock()
            init_sentry(app=app)
            mock_sentry_init.assert_called_once()
            app.add_middleware.assert_called_once()
    finally:
        # Restore env
        for k, v in env_backup.items():
            if v is not None:
                os.environ[k] = v
            else:
                os.environ.pop(k, None)
