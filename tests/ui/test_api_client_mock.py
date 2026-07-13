from streamlit_app import api_client


def test_mock_api_client_fixture(mock_api_client):
    # Verify mock_api_client fixture is active and returns the mock client
    assert mock_api_client is not None

    # Test list_books through api_client (which is monkeypatched)
    books = api_client.list_books()
    assert len(books) == 1
    assert books[0]["title"] == "テスト用の本"

    # Add a mock book and retrieve it
    mock_api_client.add_mock_book(2, "もう一つの本", "SF", 3)
    books = api_client.list_books()
    assert len(books) == 2
    assert books[1]["title"] == "もう一つの本"

    # Test delete_book
    success = api_client.delete_book(1)
    assert success is True
    books = api_client.list_books()
    assert len(books) == 1
    assert books[0]["id"] == 2
