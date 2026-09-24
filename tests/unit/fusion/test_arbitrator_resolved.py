"""Unit tests for resolved conflicts override in Arbitrator."""
from src.fusion.arbitrator import Arbitrator
from src.fusion.config import FusionConfig
from src.fusion.models import Conflict, SourceVector
from src.pipeline.emotional_residue import EmotionalVector, EmotionalSignal, EmotionType
from src.stores.conflict_store import ConflictStore


def test_resolved_conflict_overrides(tmp_path):
    conflict_file = tmp_path / "conflicts.jsonl"
    resolution_store = ConflictStore(conflict_file)
    config = FusionConfig(mode="weighted_blend")

    arbitrator = Arbitrator(config, resolution_store=resolution_store)

    # 矛盾する2つのシグナル
    vec_anno = EmotionalVector(episode_id="ep15")
    vec_anno.set_signal(EmotionalSignal("A", "D", EmotionType.TRUST, 0.7, 1.0, "...", "ep15"))
    sv_anno = SourceVector("annotation", vec_anno, 1.0)

    vec_pipe = EmotionalVector(episode_id="ep15")
    vec_pipe.set_signal(EmotionalSignal("A", "D", EmotionType.TRUST, -0.5, 0.5, "...", "ep15"))
    sv_pipe = SourceVector("pipeline", vec_pipe, 0.5)

    # まず1回検知して conflict_id を得る
    detector = arbitrator.conflict_detector
    conflicts = detector.detect([sv_anno, sv_pipe])
    assert len(conflicts) == 1
    cid = conflicts[0].conflict_id

    # 解決ストアに「手動値 0.55」で記録
    resolution_store.resolve_conflict(cid, resolution="manual", manual_value=0.55)

    # 融合実行
    fused = arbitrator.fuse([sv_anno, sv_pipe])
    val = fused.get_value("A", "D", EmotionType.TRUST)
    assert val is not None
    assert val.value == 0.55  # 手動解決値が強制適用
    assert val.primary_source == "manual"
    assert val.confidence == 1.0  # 解決済みは信頼度 1.0
