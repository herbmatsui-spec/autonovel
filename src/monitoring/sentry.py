import os
import sentry_sdk
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware

def init_sentry(app=None):
    """
    Initialize Sentry error tracking.
    If app is provided, attaches the ASGI middleware.
    Skips initialization in testing environment to avoid overhead.
    """
    if os.environ.get("TESTING") == "True" or "PYTEST_CURRENT_TEST" in os.environ:
        return None

    dsn = os.environ.get("SENTRY_DSN")
    if dsn:
        sentry_sdk.init(
            dsn=dsn,
            traces_sample_rate=1.0,
            # Set traces_sample_rate to 1.0 to capture 100% of transactions for performance monitoring.
            # We recommend adjusting this value in production.
        )
        if app is not None:
            app.add_middleware(SentryAsgiMiddleware)
    # If no DSN, Sentry is disabled (useful for development)