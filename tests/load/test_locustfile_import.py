def test_locustfile_imports():
    """Test that the locustfile can be imported and the WebsiteUser class is defined."""
    # Try to import the locustfile
    try:
        from tests.load.test_locustfile import WebsiteUser
        assert WebsiteUser is not None
    except ImportError as e:
        raise AssertionError(f"Failed to import locustfile: {e}")