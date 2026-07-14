import os
from fastapi.testclient import TestClient

# Import the FastAPI application instance



def get_expected_origins() -> list[str]:
    """Return the list of origins that the CORS middleware should allow.
    Mirrors the logic in `config/cors_config.py`.
    """
    import json
    origins_env = os.getenv("CORS_ALLOWED_ORIGINS", "")
    if origins_env:
        try:
            parsed = json.loads(origins_env)
            if isinstance(parsed, list):
                return [o.strip() for o in parsed if isinstance(o, str) and o.strip()]
        except json.JSONDecodeError:
            pass
        return [o.strip() for o in origins_env.split(",") if o.strip()]
    # Default origins defined in config/cors_config.py
    return ["http://localhost:5173", "http://localhost:8501"]


def test_health_cors_header():
    test_origin = "http://example.com"
    os.environ["CORS_ALLOWED_ORIGINS"] = f'["{test_origin}"]'
    from src.backend.server import app
    client = TestClient(app)
    response = client.get("/health", headers={"Origin": test_origin})
    assert response.status_code == 200, "Health endpoint should return 200"
    # The CORS middleware should echo back the origin if it is allowed.
    allowed = get_expected_origins()
    header_value = response.headers.get("access-control-allow-origin")
    assert header_value in allowed, f"CORS header '{header_value}' not in allowed list {allowed}"
