def test_key_phrase_tests():
    import logging
    import pytest
    from src.models.sharp_edge import SharpEdgeSpec
    from pydantic import ValidationError

    def test_key_phrase_default_empty():
        edge = SharpEdgeSpec(
            edge_type="ending_pullback",
            description="余韻のある終わり方",
        )
        assert edge.key_phrase == ""

    def test_key_phrase_20_chars_ok(self):
        edge = SharpEdgeSpec(
            edge_type="ending_pullback",
            description="余韻のある終わり方",
            key_phrase="余韻のある終わり方を",
        )
        assert len(edge.key_phrase) == 10  # 10 chars in Japanese

    def test_key_phrase_21_chars_raises(self):
        with pytest.raises(ValidationError):
            SharpEdgeSpec(
                edge_type="ending_pullback",
                description="余韻のある終わり方",
                key_phrase="あ" * 21,
            )

    def test_key_phrase_20_chars_exact_ok(self):
        edge = SharpEdgeSpec(
            edge_type="ending_pullback",
            description="余韻のある終わり方",
            key_phrase="あ" * 20,
        )
        assert len(edge.key_phrase) == 20

if __name__ == "__main__":
    test_key_phrase_tests()
    print("All tests passed!")