    def test_create_snapshot_returns_empty_if_source_not_exists(self):
        """Test that create_snapshot returns empty string when source does not exist"""
        with patch('pathlib.Path.exists', return_value=False):
            result = WorkspaceManager.create_snapshot("/nonexistent.db")
            assert result == ""

