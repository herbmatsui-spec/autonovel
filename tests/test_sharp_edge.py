"""
tests/test_sharp_edge.py
src/models/sharp_edge.py の単体テスト。
"""
import logging

import pytest
from pydantic import ValidationError

from src.models.sharp_edge import SharpEdgeSpec


class TestSharpEdgeSpec:
    def test_valid_ending_pullback(self):
        edge = SharpEdgeSpec(
            edge_type="ending_pullback",
            description="余韻のある終わり方",
            preserve_on_quality_polish=True,
        )
        assert edge.edge_type == "ending_pullback"
        assert edge.preserve_on_quality_polish is True

    def test_description_max_length(self):
        long_desc = "a" * 201
        with pytest.raises(ValidationError):
            SharpEdgeSpec(
                edge_type="ending_pullback",
                description=long_desc,
            )

    def test_description_200_chars_ok(self):
        desc = "a" * 200
        edge = SharpEdgeSpec(
            edge_type="ending_pullback",
            description=desc,
        )
        assert len(edge.description) == 200

    def test_unknown_edge_type_raises(self):
        with pytest.raises(ValidationError):
            SharpEdgeSpec(
                edge_type="unknown_type",
                description="テスト",
            )

    def test_empty_edge_type_raises(self):
        with pytest.raises(ValidationError):
            SharpEdgeSpec(
                edge_type="",
                description="テスト",
            )

    def test_preserve_false_logs_warning(self, caplog):
        with caplog.at_level(logging.WARNING):
            SharpEdgeSpec(
                edge_type="protagonist_flaw",
                description="テスト",
                preserve_on_quality_polish=False,
            )
        assert "preserve_on_quality_polish=False" in caplog.text

    def test_key_phrase_default_empty(self):
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
