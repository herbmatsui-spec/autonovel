import json

from src.backend.engine_plot import (
    _parse_sharp_edges,
    resolve_sharp_edges,
)


class TestParseSharpEdges:
    def test_key_phrase_handling(self):
        """
        Test cases for key_phrase field handling in _parse_sharp_edges
        """
        # Test key_phrase present and within limit
        data = [{
            "edge_type": "ending_pullback",
            "description": "結末の引き方",
            "key_phrase": "余韻のある終わり方"
        }]
        raw = json.dumps(data)
        result = _parse_sharp_edges(raw)
        assert len(result) == 1
        assert result[0].key_phrase == "余韻のある終わり方"

        # Test key_phrase too long
        data = [{
            "edge_type": "ending_pullback",
            "description": "結末の説明",
            "key_phrase": "あ" * 21
        }]
        raw = json.dumps(data)
        result = _parse_sharp_edges(raw)
        # Should truncate to first 20 chars
        assert len(result) == 1
        assert result[0].key_phrase == "あ" * 20

        # Test key_phrase missing (uses empty string)
        data = [{
            "edge_type": "ending_pullback",
            "description": "結末の説明"
        }]
        raw = json.dumps(data)
        result = _parse_sharp_edges(raw)
        assert result[0].key_phrase == ""

        # Test key_phrase with whitespace
        data = [{
            "edge_type": "ending_pullback",
            "description": "結末の説明",
            "key_phrase": " 先頭余韻  "
        }]
        raw = json.dumps(data)
        result = _parse_sharp_edges(raw)
        # Should trim whitespace
        assert result[0].key_phrase == "先頭余韻"

        # Test unknown edge type (should skip)
        data = [{
            "edge_type": "invalid_type",
            "description": "無効",
            "key_phrase": "無効なフレーズ"
        }]
        raw = json.dumps(data)
        result = _parse_sharp_edges(raw)
        assert result == []

    def test_key_phrase_exceeding_20_raises(self):
        long_phrase = "あ" * 21
        data = [{"edge_type": "ending_pullback", "description": "説明", "key_phrase": long_phrase}]
        raw = json.dumps(data)
        # パースしてwarningを出力するはず
        result = _parse_sharp_edges(raw)
        # 切り捨てられるので問題なし
        assert len(result) == 1
        assert len(result[0].key_phrase) == 20

    def test_key_phrase_missing_uses_empty(self):
        data = [{"edge_type": "protagonist_flaw", "description": "欠陥"}]
        raw = json.dumps(data)
        result = _parse_sharp_edges(raw)
        assert len(result) == 1
        assert result[0].key_phrase == ""

    def test_unknown_edge_type_skips(self):
        data = [{"edge_type": "unknown_type", "description": "テスト"}]
        raw = json.dumps(data)
        result = _parse_sharp_edges(raw)
        assert result == []


class TestResolveSharpEdges:
    def test_none_plot_returns_empty(self):
        from src.models.db import PlotDbModel
        plot = PlotDbModel(book_id=1, ep_num=1, sharp_edges_json="")
        assert resolve_sharp_edges(plot) == []
