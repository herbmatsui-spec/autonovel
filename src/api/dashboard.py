"""Dashboard data API for emotional timeline, conflicts summary and source contribution."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Query

from src.fusion.engine import FusionEngine
from src.stores.conflict_store import ConflictStore
from src.stores.vector_store import VectorStore

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

_engine_instance: Optional[FusionEngine] = None


def get_dashboard_engine() -> FusionEngine:
    global _engine_instance
    if _engine_instance is None:
        from src.stores.vector_store import RedisVectorStore
        store = RedisVectorStore(skip_connection_check=True)
        _engine_instance = FusionEngine(store)
    return _engine_instance


def set_dashboard_engine(engine: FusionEngine) -> None:
    global _engine_instance
    _engine_instance = engine


@router.get("/timeline")
def get_timeline(
    pair: str = Query(..., description="ペア 'A,B' または 'A->B'"),
    from_ep: int = Query(1, alias="from", description="開始話"),
    to_ep: int = Query(20, alias="to", description="終了話"),
):
    """Chart.js 互換の時系列感情データ返却"""
    engine = get_dashboard_engine()
    if "," in pair:
        p_tuple = tuple(pair.split(",", 1))
    elif "->" in pair:
        p_tuple = tuple(pair.split("->", 1))
    else:
        p_tuple = (pair, "")

    labels = [f"Ep{ep}" for ep in range(from_ep, to_ep + 1)]
    # 各ソース別の系列と、融合系列を生成
    datasets = []
    fused_points = []
    source_points: Dict[str, List[Optional[float]]] = {"annotation": [], "rule_engine": [], "pipeline": []}

    for ep in range(from_ep, to_ep + 1):
        sources = engine.collector.collect_all(p_tuple, episode=ep)
        fused = engine.arbitrator.fuse(sources)
        # 代表感情（主要な感情）を取得
        fval = next((v.value for k, v in fused.values.items() if (k[0], k[1]) == p_tuple), None)
        fused_points.append(fval)

        # ソース別
        ep_src_map = {}
        for sv in sources:
            emo_dict = sv.vector.get_pair_emotions(p_tuple[0], p_tuple[1])
            val = next(iter(emo_dict.values()), None) if emo_dict else None
            ep_src_map[sv.namespace] = val

        for ns in source_points.keys():
            source_points[ns].append(ep_src_map.get(ns))

    datasets.append({
        "label": f"Fused ({pair})",
        "data": fused_points,
        "borderColor": "#4F46E5",
        "tension": 0.3,
    })
    colors = {"annotation": "#10B981", "rule_engine": "#F59E0B", "pipeline": "#6B7280"}
    for ns, data in source_points.items():
        datasets.append({
            "label": f"{ns} ({pair})",
            "data": data,
            "borderColor": colors.get(ns, "#000000"),
            "borderDash": [5, 5],
        })

    return {
        "labels": labels,
        "datasets": datasets,
        "meta": {"pair": list(p_tuple), "from": from_ep, "to": to_ep},
    }


@router.get("/conflicts")
def get_conflicts_summary(
    from_ep: int = Query(1, alias="from"),
    to_ep: int = Query(50, alias="to"),
):
    """期間内矛盾サマリー（件数・傾向）"""
    engine = get_dashboard_engine()
    store = engine.conflict_store
    all_conflicts = store.get_all_conflicts()

    filtered = []
    for c in all_conflicts:
        # conflict_id や metadata からエピソードを判定
        filtered.append(c.to_dict())

    return {
        "total_conflicts": len(filtered),
        "conflicts": filtered,
        "range": {"from": from_ep, "to": to_ep},
    }


@router.get("/source_contribution")
def get_source_contribution(episode: int = Query(..., description="エピソード番号")):
    """指定話のソース別採用率統計"""
    engine = get_dashboard_engine()
    fused = engine.fuse_all(episode)

    counts = {"annotation": 0, "rule_engine": 0, "pipeline": 0, "manual": 0}
    total = len(fused.values)
    for fval in fused.values.values():
        counts[fval.primary_source] = counts.get(fval.primary_source, 0) + 1

    ratios = {k: (v / total if total > 0 else 0.0) for k, v in counts.items()}
    return {
        "episode": episode,
        "total_values": total,
        "counts": counts,
        "ratios": ratios,
    }
