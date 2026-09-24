"""Comprehensive regression tests for Week 4 Fusion Layer."""
import pytest
from src.agents.writer_agent import WriterAgent
from src.fusion.alerts import ConflictAlerter
from src.fusion.arbitrator import Arbitrator
from src.fusion.config import FusionConfig
from src.fusion.conflict_detector import ConflictDetector
from src.fusion.engine import FusionEngine
from src.fusion.models import SourceVector
from src.pipeline.emotional_residue import EmotionalVector, EmotionalSignal, EmotionType
from src.pipeline.prompt_builder import build_fused_emotional_context_prompt
from src.stores.conflict_store import ConflictStore
from src.stores.vector_store import InMemoryVectorStore


def test_annotation_wins_no_conflict():
    config = FusionConfig()
    arbitrator = Arbitrator(config)

    v_anno = EmotionalVector(episode_id="ep1")
    v_anno.set_signal(EmotionalSignal("A", "B", EmotionType.FEAR, 0.9, 1.0, "...", "ep1"))
    sv_anno = SourceVector("annotation", v_anno, 1.0)

    fused = arbitrator.fuse([sv_anno])
    val = fused.get_value("A", "B", EmotionType.FEAR)
    assert val is not None
    assert val.primary_source == "annotation"
    assert val.value == 0.9


def test_rule_engine_fallback():
    config = FusionConfig()
    arbitrator = Arbitrator(config)

    v_rule = EmotionalVector(episode_id="ep1")
    v_rule.set_signal(EmotionalSignal("A", "B", EmotionType.TENSION, 0.6, 0.8, "...", "ep1"))
    sv_rule = SourceVector("rule_engine", v_rule, 0.8)

    v_pipe = EmotionalVector(episode_id="ep1")
    v_pipe.set_signal(EmotionalSignal("A", "B", EmotionType.TENSION, 0.3, 0.5, "...", "ep1"))
    sv_pipe = SourceVector("pipeline", v_pipe, 0.5)

    fused = arbitrator.fuse([sv_rule, sv_pipe])
    val = fused.get_value("A", "B", EmotionType.TENSION)
    assert val is not None
    assert val.primary_source == "rule_engine"
    assert val.value == 0.6


def test_pipeline_last_resort():
    config = FusionConfig()
    arbitrator = Arbitrator(config)

    v_pipe = EmotionalVector(episode_id="ep1")
    v_pipe.set_signal(EmotionalSignal("A", "B", EmotionType.AFFECTION, 0.4, 0.5, "...", "ep1"))
    sv_pipe = SourceVector("pipeline", v_pipe, 0.5)

    fused = arbitrator.fuse([sv_pipe])
    val = fused.get_value("A", "B", EmotionType.AFFECTION)
    assert val is not None
    assert val.primary_source == "pipeline"
    assert val.value == 0.4


def test_conflict_detected_sign_flip():
    config = FusionConfig(conflict_threshold=0.3, significance_threshold=0.3)
    detector = ConflictDetector(config)

    v1 = EmotionalVector(episode_id="ep1")
    v1.set_signal(EmotionalSignal("A", "B", EmotionType.TRUST, 0.8, 1.0, "...", "ep1"))
    sv1 = SourceVector("annotation", v1, 1.0)

    v2 = EmotionalVector(episode_id="ep1")
    v2.set_signal(EmotionalSignal("A", "B", EmotionType.TRUST, -0.7, 0.5, "...", "ep1"))
    sv2 = SourceVector("pipeline", v2, 0.5)

    conflicts = detector.detect([sv1, sv2])
    assert len(conflicts) == 1
    assert conflicts[0].pair == ("A", "B")
    assert conflicts[0].emotion == EmotionType.TRUST


def test_conflict_blend_mode():
    config = FusionConfig(
        source_confidence={"annotation": 1.0, "pipeline": 0.5},
        blend_weights={"annotation": 0.7, "pipeline": 0.3},
        mode="weighted_blend",
        conflict_penalty=0.2,
    )
    arbitrator = Arbitrator(config)

    v1 = EmotionalVector(episode_id="ep1")
    v1.set_signal(EmotionalSignal("A", "B", EmotionType.FEAR, 0.8, 1.0, "...", "ep1"))
    sv1 = SourceVector("annotation", v1, 1.0)

    v2 = EmotionalVector(episode_id="ep1")
    v2.set_signal(EmotionalSignal("A", "B", EmotionType.FEAR, -0.6, 0.5, "...", "ep1"))
    sv2 = SourceVector("pipeline", v2, 0.5)

    fused = arbitrator.fuse([sv1, sv2])
    assert len(fused.conflicts) == 1
    val = fused.get_value("A", "B", EmotionType.FEAR)
    assert 0.5 < val.value < 0.6
    assert pytest.approx(val.confidence, 0.01) == 0.8


def test_manual_resolution_persists(tmp_path):
    store_file = tmp_path / "conflicts.jsonl"
    res_store = ConflictStore(store_file)
    config = FusionConfig()
    arbitrator = Arbitrator(config, resolution_store=res_store)

    v1 = EmotionalVector(episode_id="ep1")
    v1.set_signal(EmotionalSignal("A", "B", EmotionType.FEAR, 0.8, 1.0, "...", "ep1"))
    sv1 = SourceVector("annotation", v1, 1.0)

    v2 = EmotionalVector(episode_id="ep1")
    v2.set_signal(EmotionalSignal("A", "B", EmotionType.FEAR, -0.6, 0.5, "...", "ep1"))
    sv2 = SourceVector("pipeline", v2, 0.5)

    cid = arbitrator.conflict_detector.detect([sv1, sv2])[0].conflict_id
    res_store.resolve_conflict(cid, resolution="manual", manual_value=0.25)

    fused = arbitrator.fuse([sv1, sv2])
    val = fused.get_value("A", "B", EmotionType.FEAR)
    assert val.value == 0.25
    assert val.primary_source == "manual"
    assert val.confidence == 1.0


def test_fused_prompt_format():
    store = InMemoryVectorStore()
    config = FusionConfig(
        source_confidence={"annotation": 1.0, "rule_engine": 0.6, "pipeline": 0.3}
    )
    v1 = EmotionalVector(episode_id="ep1")
    v1.set_signal(EmotionalSignal("A", "B", EmotionType.FEAR, 0.8, 1.0, "...", "ep1"))
    store.upsert("annotation", "ep1:A->B", v1)

    v2 = EmotionalVector(episode_id="ep1")
    v2.set_signal(EmotionalSignal("A", "C", EmotionType.TENSION, 0.4, 0.6, "...", "ep1"))
    store.upsert("rule_engine", "ep1:A->C", v2)

    engine = FusionEngine(store, config)
    prompt = build_fused_emotional_context_prompt(episode_id=2, fusion_engine=engine)
    assert "[直前話からの引き継ぎ感情（融合済み）]" in prompt
    assert "高信頼度（作者指定・プロット整合）" in prompt
    assert "中信頼度（プロットルール推定）" in prompt


def test_alert_on_conflict():
    alerter = ConflictAlerter(FusionConfig(alert_channels=["log"]))
    v1 = EmotionalVector(episode_id="ep1")
    v1.set_signal(EmotionalSignal("A", "B", EmotionType.FEAR, 0.8, 1.0, "...", "ep1"))
    sv1 = SourceVector("annotation", v1, 1.0)

    v2 = EmotionalVector(episode_id="ep1")
    v2.set_signal(EmotionalSignal("A", "B", EmotionType.FEAR, -0.6, 0.5, "...", "ep1"))
    sv2 = SourceVector("pipeline", v2, 0.5)

    detector = ConflictDetector(FusionConfig())
    conflicts = detector.detect([sv1, sv2])
    res = alerter.alert(conflicts, episode=1)
    assert res["status"] == "alerted"
    assert res["payload"]["conflict_count"] == 1
