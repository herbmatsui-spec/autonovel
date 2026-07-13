class ApiClient:
    """Placeholder API client."""
    def __init__(self, api_key: str):
        self.api_key = api_key

    def request(self, *args, **kwargs):
        # Stub implementation
        return {}


def get_client(api_key: str) -> ApiClient:
    """Return a shared ApiClient instance (simple factory)."""
    return ApiClient(api_key)
