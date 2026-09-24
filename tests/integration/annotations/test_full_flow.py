"""Full flow integration test for annotations (editor -> API -> store -> prompt)."""
from __future__ import annotations

import pytest
import tempfile
from unittest.mock import MagicMock, patch

from src.annotations.integrated_parser import parse_script
from src.annotations.persistence import AnnotationPersistence
from src.pipeline.prompt_builder import build_emotional_context_prompt, build_fused_emotional_context_prompt
from src.pipeline.emotional_residue import EmotionalVector, EmotionalSignal, EmotionType
from src.stores.vector_store import RedisVectorStore
from src.stores.graph_store import InMemoryGraphStore
from src.stores.event_log import EventLogStore
from src.pipeline.character_dict import load_character_dict


class TestFullAnnotationFlow:
    """エディタ→API→ストア→プロンプトの完全フロー統合テスト"""

    @pytest.fixture
    def vector_store(self):
        import fakeredis
        redis_client = fakeredis.FakeRedis(decode_responses=True)
        store = RedisVectorStore(skip_connection_check=True)
        store.client = redis_client
        return store

    @pytest.fixture
    def char_dict(self):
        return load_character_dict()

    @pytest.fixture
    def sample_script_frontmatter(self):
        """テスト用脚本（フロントマターのみ）"""
        return """---
beats:
  - source: "A"
    target: "B"
    emotion: "fear"
    delta: 0.8
    cause: "ep14 betrayal"
    confidence: 0.9
    hidden: true
  - source: "B"
    target: "A"
    emotion: "sadness"
    delta: 0.6
    cause: "ep14 betrayal"
    confidence: 0.8
    hidden: false
---
A goes to B.
"""

    def test_script_parsing_frontmatter_only(self, sample_script_frontmatter):
        """脚本パーステスト（フロントマターのみ）"""
        parsed = parse_script(sample_script_frontmatter, episode=15)
        
        assert len(parsed.beats) == 2
        assert len(parsed.frontmatter_beats) == 2
        assert len(parsed.inline_beats) == 0
        
        # フロントマター優先でマージされている
        beat_dict = {(b.source, b.target, b.emotion.value): b for b in parsed.beats}
        assert beat_dict[("A", "B", "fear")].delta == 0.8
        assert beat_dict[("B", "A", "sadness")].delta == 0.6

    def test_annotation_persistence(self, vector_store, sample_script_frontmatter):
        """アノテーション永続化テスト"""
        # パース
        parsed = parse_script(sample_script_frontmatter, episode=15)
        
        # 検証
        validator = MagicMock()
        from src.annotations.validator import ValidationResult
        validator.validate.return_value = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        # 永続化
        persistence = AnnotationPersistence(vector_store)
        count = persistence.persist_beats(parsed.beats, 15)
        assert count == 2
        
        # VectorStoreに保存確認
        stored = vector_store.get_latest("annotation", ("A", "B"))
        assert stored is not None
        
        from src.pipeline.emotional_residue import EmotionType
        fear_val = stored.get_value("A", "B", EmotionType.FEAR)
        assert fear_val == 0.8
        
        sadness_val = stored.get_value("B", "A", EmotionType.SADNESS)
        assert sadness_val == 0.6

    def test_annotation_priority_in_prompt(self, vector_store):
        """プロンプトでのアノテーション優先度テスト"""
        from src.pipeline.emotional_residue import EmotionalVector, EmotionalSignal, EmotionType
        
        # 1. annotation namespaceにデータ保存
        ann_vec = EmotionalVector(episode_id="ep15")
        ann_vec.set_signal(EmotionalSignal("A", "B", EmotionType.FEAR, 0.8, 0.9, "...", "ep15", "ep14 betrayal"))
        vector_store.upsert("annotation", "ep15", ann_vec)
        
        # 2. rule_engine namespaceにも異なるデータ保存
        rule_vec = EmotionalVector(episode_id="ep15")
        rule_vec.set_signal(EmotionalSignal("A", "B", EmotionType.FEAR, -0.5, 0.5, "...", "ep15"))
        vector_store.upsert("rule_engine", "ep15", rule_vec)
        
        # 3. pipeline namespaceにもデータ保存
        pipe_vec = EmotionalVector(episode_id="ep15")
        pipe_vec.set_signal(EmotionalSignal("A", "B", EmotionType.FEAR, 0.2, 0.3, "...", "ep15"))
        vector_store.upsert("pipeline", "ep15", pipe_vec)
        
        # 4. fused prompt で優先度確認
        fused_prompt = build_fused_emotional_context_prompt(16, vector_store)
        
        # annotationの値（0.8）が採用される
        assert "0.8" in fused_prompt
        # rule_engineの-0.5やpipelineの0.2は採用されない
        assert "-0.5" not in fused_prompt
        assert "0.2" not in fused_prompt

    def test_annotation_only_prompt(self, vector_store):
        """annotationのみの場合"""
        from src.pipeline.emotional_residue import EmotionalVector, EmotionalSignal, EmotionType
        
        vec = EmotionalVector(episode_id="ep14")
        vec.set_signal(EmotionalSignal("A", "B", EmotionType.FEAR, 0.8, 0.9, "...", "ep14", "ep14 betrayal"))
        vector_store.upsert("annotation", "ep14", vec)
        
        prompt = build_fused_emotional_context_prompt(15, vector_store)
        
        assert "0.8" in prompt
        assert "fear" in prompt

    def test_rule_engine_fallback(self, vector_store):
        """annotationなしの場合rule_engineが使われる"""
        from src.pipeline.emotional_residue import EmotionalVector, EmotionalSignal, EmotionType
        
        vec = EmotionalVector(episode_id="ep14")
        vec.set_signal(EmotionalSignal("A", "B", EmotionType.FEAR, -0.5, 0.5, "...", "ep14"))
        vector_store.upsert("rule_engine", "ep14", vec)
        
        prompt = build_fused_emotional_context_prompt(15, vector_store)
        
        assert "-0.5" in prompt

    def test_pipeline_last_resort(self, vector_store):
        """両方なしの場合pipelineが使われる"""
        from src.pipeline.emotional_residue import EmotionalVector, EmotionalSignal, EmotionType
        
        vec = EmotionalVector(episode_id="ep14")
        vec.set_signal(EmotionalSignal("A", "B", EmotionType.FEAR, 0.2, 0.3, "...", "ep14"))
        vector_store.upsert("pipeline", "ep14", vec)
        
        prompt = build_fused_emotional_context_prompt(15, vector_store)
        
        assert "0.2" in prompt

    def test_empty_prompt(self, vector_store):
        """データなしの場合"""
        prompt = build_fused_emotional_context_prompt(1, vector_store)  # ep0は存在しない
        assert prompt == ""
        
        prompt = build_fused_emotional_context_prompt(99, vector_store)  # 存在しないep
        assert prompt == ""

    def test_graph_log_consistency(self, vector_store):
        """Graph/Logストアとの整合性"""
        from src.annotations.beat import EmotionalBeat
        from src.pipeline.emotional_residue import EmotionType
        
        graph_store = InMemoryGraphStore()
        
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            log_path = f.name
        
        log_store = EventLogStore(path=log_path)
        
        # テスト用ビート
        beats = [
            EmotionalBeat(
                episode=15, scene=3, source="A", target="B",
                emotion=EmotionType.FEAR, delta=0.8,
                cause="ep14 betrayal", confidence=0.9, hidden=True,
                beat_id="beat123",
            ),
            EmotionalBeat(
                episode=15, scene=3, source="B", target="A",
                emotion=EmotionType.SADNESS, delta=0.6,
                cause="ep14 betrayal", confidence=0.8, hidden=False,
                beat_id="beat456",
            ),
        ]
        
        # 永続化
        persistence = AnnotationPersistence(vector_store, graph_store, log_store)
        count = persistence.persist_beats(beats, 15)
        
        # Graph確認
        edge_ab = graph_store.get_latest_edge("A", "B")
        assert edge_ab is not None
        assert edge_ab["fear"] == 0.8
        assert edge_ab["source_type"] == "annotation"
        
        # beat_idはpropsに含まれる
        assert edge_ab.get("beat_id") is not None or edge_ab.get("beat_id") == ""
        
        # Log確認
        signals = log_store.query(pair=("A", "B"), from_ep=15, to_ep=15)
        fear_signals = [s for s in signals if s.emotion_type.value == "fear"]
        assert len(fear_signals) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])