import sys
import os

sys.path.insert(0, ".")

def test_api_routes_import():
    print("Testing API and Routers imports...")
    try:
        from src.api.routes.ux_routes import router as ux_router
        print("  - ux_routes router loaded successfully.")
    except Exception as e:
        print(f"  [ERROR] ux_routes import failed: {e}")
        return False

    try:
        from src.backend.routers.easy_mode import router as easy_mode_router
        print("  - easy_mode router loaded successfully.")
    except Exception as e:
        print(f"  [ERROR] easy_mode router import failed: {e}")
        return False

    try:
        from src.backend.auth import require_api_key, get_api_key_service
        service = get_api_key_service()
        print(f"  - auth service loaded (disabled={service.disabled}).")
    except Exception as e:
        print(f"  [ERROR] auth service import failed: {e}")
        return False

    print("All route imports verified successfully!")
    return True

if __name__ == "__main__":
    if not test_api_routes_import():
        sys.exit(1)
