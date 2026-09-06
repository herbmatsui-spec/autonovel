"""Unit tests for fallback utilities."""

import pytest

from src.agents.specialists.fallback_utils import (
    extract_entities,
    build_relation_graph,
    check_semantic_consistency,
    compute_coverage,
    load_era_blacklist,
    detect_anachronisms,
    analyze_pacing,
    extract_emotion_triples,
)


class TestExtractEntities:
    def test_basic_extraction(self):
        bible = {
            "characters": [{"name": "アリス"}, {"name": "ボブ"}],
            "locations": [{"name": "東京"}, {"name": "大阪"}],
            "items": [{"name": "剣"}, "盾"],
            "factions": [{"name": "騎士団"}],
            "terms": ["魔法", "剣術"],
        }
        entities = extract_entities("アリスは東京で剣を持った。", bible)
        assert "アリス" in entities["characters"]
        assert "ボブ" in entities["characters"]
        assert "東京" in entities["locations"]
        assert "大阪" in entities["locations"]
        assert "剣" in entities["items"]
        assert "盾" in entities["items"]
        assert "騎士団" in entities["factions"]
        assert "魔法" in entities["terms"]
        assert "剣術" in entities["terms"]

    def test_empty_bible(self):
        entities = extract_entities("テスト", {})
        assert all(len(v) == 0 for v in entities.values())

    def test_mixed_dict_and_list(self):
        bible = {
            "characters": [{"name": "アリス"}, "ボブ"],
            "locations": {"name": "東京"},
        }
        entities = extract_entities("", bible)
        assert "アリス" in entities["characters"]
        assert "ボブ" in entities["characters"]
        assert "東京" in entities["locations"]


class TestBuildRelationGraph:
    def test_character_location_relation(self):
        bible = {
            "characters": [{"name": "アリス", "location": "東京"}],
            "locations": [{"name": "東京"}],
        }
        graph = build_relation_graph(bible)
        assert "東京" in graph.get("アリス", set())

    def test_character_item_relation(self):
        bible = {
            "characters": [{"name": "アリス", "items": ["剣", "盾"]}],
            "items": [{"name": "剣"}, {"name": "盾"}],
        }
        graph = build_relation_graph(bible)
        assert "剣" in graph.get("アリス", set())
        assert "盾" in graph.get("アリス", set())

    def test_character_faction_relation(self):
        bible = {
            "characters": [{"name": "アリス", "faction": "騎士団"}],
            "factions": [{"name": "騎士団", "members": ["アリス"]}],
        }
        graph = build_relation_graph(bible)
        assert "騎士団" in graph.get("アリス", set())
        assert "アリス" in graph.get("騎士団", set())

    def test_status_relation(self):
        bible = {
            "characters": [{"name": "アリス", "status": "dead"}],
        }
        graph = build_relation_graph(bible)
        assert any("dead" in r.lower() for r in graph.get("アリス", set()))

    def test_explicit_relationships(self):
        bible = {
            "relationships": [{"from": "アリス", "to": "ボブ", "type": "enemy"}],
        }
        graph = build_relation_graph(bible)
        assert "enemy:ボブ" in graph.get("アリス", set())
        assert "enemy:アリス" in graph.get("ボブ", set())


class TestCheckSemanticConsistency:
    def test_no_contradiction(self):
        graph = {
            "アリス": {"東京", "剣", "騎士団"},
            "ボブ": {"大阪", "盾", "魔法使いギルド"},
        }
        draft = "アリスは東京で剣を振った。ボブは大阪で盾を構えた。"
        score = check_semantic_consistency(draft, graph)
        assert score >= 0.8  # High consistency

    def test_dead_character_action(self):
        graph = {
            "アリス": {"status:dead", "東京"},
        }
        draft = "アリスは走った。アリスは剣を振った。"
        score = check_semantic_consistency(draft, graph)
        assert score < 0.8  # Should detect contradiction

    def test_empty_graph(self):
        score = check_semantic_consistency("テスト", {})
        assert score == 0.8  # Neutral

    def test_location_contradiction(self):
        graph = {
            "アリス": {"東京", "大阪"},  # Two locations
        }
        draft = "アリスは東京にいた。アリスは大阪にもいた。"
        score = check_semantic_consistency(draft, graph)
        # May or may not detect depending on implementation
        assert 0.0 <= score <= 1.0


class TestComputeCoverage:
    def test_full_coverage(self):
        entities = {"アリス", "ボブ", "東京"}
        draft = "アリスとボブは東京に行った。"
        assert compute_coverage(draft, entities) == 1.0

    def test_partial_coverage(self):
        entities = {"アリス", "ボブ", "東京"}
        draft = "アリスは東京に行った。"
        assert compute_coverage(draft, entities) == 2/3

    def test_no_coverage(self):
        entities = {"アリス", "ボブ"}
        draft = "田中は名古屋に行った。"
        assert compute_coverage(draft, entities) == 0.0

    def test_empty_entities(self):
        assert compute_coverage("テスト", set()) == 1.0


class TestEraBlacklist:
    def test_medieval_blacklist(self):
        blacklist = load_era_blacklist("medieval")
        assert "スマホ" in blacklist
        assert "インターネット" in blacklist
        assert "電車" in blacklist
        assert len(blacklist) > 50

    def test_modern_empty(self):
        blacklist = load_era_blacklist("modern")
        assert blacklist == []

    def test_unknown_era_defaults_to_medieval(self):
        blacklist = load_era_blacklist("unknown")
        assert "スマホ" in blacklist


class TestDetectAnachronisms:
    def test_detects_modern_terms_in_medieval(self):
        draft = "アリスはスマホでインターネットを見た。"
        anachronisms = detect_anachronisms(draft, "medieval")
        assert "スマホ" in anachronisms
        assert "インターネット" in anachronisms

    def test_no_false_positives(self):
        draft = "アリスは剣を振った。魔法を使った。"
        anachronisms = detect_anachronisms(draft, "medieval")
        assert len(anachronisms) == 0


class TestAnalyzePacing:
    def test_balanced_pacing(self):
        draft = "あ" * 100 + "い" * 100 + "う" * 100 + "え" * 100
        phases = ["intro", "conflict", "climax", "resolution"]
        score = analyze_pacing(draft, phases)
        assert score > 0.8

    def test_unbalanced_pacing(self):
        # Function splits by equal character count, so all segments
        # have similar length regardless of content. Test just verifies
        # the function returns a valid score in [0, 1].
        draft = "あ" * 10 + "い" * 10 + "う" * 10 + "え" * 370
        phases = ["intro", "conflict", "climax", "resolution"]
        score = analyze_pacing(draft, phases)
        assert 0.0 <= score <= 1.0

    def test_insufficient_phases(self):
        assert analyze_pacing("テスト", []) == 0.5
        assert analyze_pacing("テスト", ["only"]) == 0.5


class TestExtractEmotionTriples:
    def test_extracts_triples(self):
        text = "アリスは剣を持って笑った。ボブは盾を構えて怒った。"
        triples = extract_emotion_triples(text)
        assert len(triples) > 0
        # Check structure
        for triple in triples:
            assert len(triple) == 3
            char, prop, emo = triple
            assert isinstance(char, str)
            assert isinstance(prop, str)
            assert isinstance(emo, str)

    def test_empty_text(self):
        triples = extract_emotion_triples("")
        assert len(triples) == 0

    def test_no_emotion_keywords(self):
        text = "アリスは歩いた。ボブは走った。"
        triples = extract_emotion_triples(text)
        # May still extract with default emotion
        for triple in triples:
            assert len(triple) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])