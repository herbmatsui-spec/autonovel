import pytest
from fastapi import FastAPI

# Import the function under test
from src.backend.server import configure_cors

@pytest.fixture
def app():
    return FastAPI()

def test_cors_rejects_wildcard_origin(monkeypatch, app):
    # Force get_allowed_origins to return a wildcard list
    monkeypatch.setattr("src.backend.server.get_allowed_origins", lambda: ["*"], raising=False)
    with pytest.raises(ValueError) as exc:
        configure_cors(app)
    assert "allow_credentials=True is incompatible with allow_origins=['*']" in str(exc.value)

def test_cors_accepts_specific_origin(monkeypatch, app):
    # Return a safe specific origin list
    monkeypatch.setattr("src.backend.server.get_allowed_origins", lambda: ["https://example.com"], raising=False)
    # Should not raise any exception
    configure_cors(app)
    # The middleware should be attached – we can inspect the middleware list
    middleware_names = [m.cls.__name__ for m in app.user_middleware]
    assert "CORSMiddleware" in middleware_names
