"""Debug CLI for inspecting and explaining fusion process."""
from __future__ import annotations

import json
from typing import Optional
import typer

from src.fusion.config import load_fusion_config
from src.fusion.engine import FusionEngine
from src.pipeline.emotional_residue import EmotionType
from src.stores.vector_store import RedisVectorStore, VectorStore

app = typer.Typer(name="fusion", help="Fusion process debug CLI")


def get_default_engine(vector_store: Optional[VectorStore] = None) -> FusionEngine:
    if vector_store is None:
        try:
            vector_store = RedisVectorStore(skip_connection_check=True)
        except Exception:
            from src.stores.vector_store import InMemoryVectorStore
            vector_store = InMemoryVectorStore()
    return FusionEngine(vector_store, load_fusion_config())


@app.command(name="show")
def show(
    episode: int = typer.Option(..., "--episode", "-e", help="エピソード番号"),
    source_char: str = typer.Option(..., "--source", "-s", help="感情の主体"),
    target_char: str = typer.Option(..., "--target", "-t", help="感情の対象"),
    json_output: bool = typer.Option(False, "--json", help="JSON形式で出力"),
):
    """指定ペアの各ソース値と融合結果、矛盾を表示"""
    engine = get_default_engine()
    pair = (source_char, target_char)
    sources = engine.collector.collect_all(pair, episode=episode)
    fused_pair = engine.arbitrator.fuse(sources)

    result = {
        "episode": episode,
        "pair": list(pair),
        "sources": [
            {
                "namespace": sv.namespace,
                "confidence": sv.confidence,
                "values": {
                    emo.value: val
                    for emo, val in sv.vector.get_pair_emotions(source_char, target_char).items()
                },
            }
            for sv in sources
        ],
        "fused": {
            emo.value: fval.to_dict()
            for (src, tgt, emo), fval in fused_pair.values.items()
            if src == source_char and tgt == target_char
        },
        "conflicts": [c.to_dict() for c in fused_pair.conflicts],
    }

    if json_output:
        typer.echo(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        typer.echo(f"=== Episode {episode}: {source_char} -> {target_char} ===")
        typer.echo(f"Collected sources: {len(sources)}")
        for s in result["sources"]:
            typer.echo(f"  [{s['namespace']}] conf={s['confidence']} values={s['values']}")
        typer.echo("Fused values:")
        for emo, fval in result["fused"].items():
            typer.echo(f"  {emo}: {fval['value']} (primary={fval['primary_source']}, conf={fval['confidence']})")
        if result["conflicts"]:
            typer.echo(f"Conflicts ({len(result['conflicts'])}):")
            for c in result["conflicts"]:
                typer.echo(f"  {c['emotion']}: {c['sources']}")


@app.command(name="conflicts")
def conflicts(
    episode: int = typer.Option(..., "--episode", "-e", help="エピソード番号"),
    json_output: bool = typer.Option(False, "--json", help="JSON形式で出力"),
):
    """指定話の矛盾一覧を表示"""
    engine = get_default_engine()
    conflicts_list = engine.conflict_store.get_conflicts_by_episode(episode)
    data = [c.to_dict() for c in conflicts_list]
    if json_output:
        typer.echo(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        typer.echo(f"=== Conflicts for Episode {episode} ({len(conflicts_list)}) ===")
        for c in conflicts_list:
            typer.echo(f"[{c.conflict_id}] {c.pair[0]}->{c.pair[1]} {c.emotion.value}: {c.sources}")


@app.command(name="explain")
def explain(
    episode: int = typer.Option(..., "--episode", "-e", help="エピソード番号"),
    source_char: str = typer.Option(..., "--source", "-s", help="感情の主体"),
    target_char: str = typer.Option(..., "--target", "-t", help="感情の対象"),
    emotion: str = typer.Option(..., "--emotion", help="感情名 (fear, affection, etc.)"),
):
    """なぜこの融合値になったかを詳細解説"""
    engine = get_default_engine()
    pair = (source_char, target_char)
    sources = engine.collector.collect_all(pair, episode=episode)
    fused_pair = engine.arbitrator.fuse(sources)

    try:
        emo_type = EmotionType(emotion.lower())
    except ValueError:
        typer.echo(f"Unknown emotion: {emotion}")
        return

    fval = fused_pair.get_value(source_char, target_char, emo_type)
    if not fval:
        typer.echo(f"No fused value found for {source_char}->{target_char}:{emotion}")
        return

    typer.echo(f"=== Explanation: {source_char}->{target_char}:{emotion} (Ep {episode}) ===")
    typer.echo(f"Final Value: {fval.value}")
    typer.echo(f"Primary Source: {fval.primary_source}")
    typer.echo(f"Contributing Sources: {fval.contributing_sources}")
    typer.echo(f"Confidence: {fval.confidence}")
    typer.echo(f"Arbitration Mode: {engine.config.mode}")

    conflict_for_emo = [c for c in fused_pair.conflicts if c.pair == pair and c.emotion == emo_type]
    if conflict_for_emo:
        typer.echo(f"Conflict Status: CONFLICT DETECTED ({conflict_for_emo[0].sources})")
        typer.echo(f"Applied Penalty: {engine.config.conflict_penalty}")
    else:
        typer.echo("Conflict Status: NONE")


if __name__ == "__main__":
    app()
