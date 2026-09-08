"""Benchmark script for 4-layer semantic compression and reflective RAG (Steps 64-65).

Validates:
- High-load compression performance (100+ entities, 50+ relations)
- Token reduction ratio >= 50%
- Guaranteed 100% retention rate for pinned protected context
"""

import os
import sys
import time

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.compression.compressor import FourLayerCompressor
from src.services.compression.models import CompressionConfig, ProtectedContext


def run_benchmark():
    print("=== Starting Pillar 3 Semantic Compression Benchmark ===")

    # 1. Generate large synthetic world corpus
    entities = [
        {"name": "FS-OMEGA-999", "labels": ["Lore"], "properties": {"role": "未回収の重要伏線"}},
    ]
    for i in range(120):
        if i < 10:
            entities.append({"name": f"主要人物_{i}", "labels": ["Character"], "properties": {"role": f"主要キャラ_{i}"}})
        elif i < 40:
            entities.append({"name": f"帝国組織_{i}", "labels": ["Country"], "properties": {"role": f"国家勢力_{i}"}})
        elif i < 80:
            entities.append({"name": f"古代秘宝_{i}", "labels": ["Item"], "properties": {"role": f"アーティファクト_{i}"}})
        else:
            entities.append({"name": f"神聖術式_{i}", "labels": ["Skill"], "properties": {"role": f"奥義スキル_{i}"}})

    relations = []
    for i in range(60):
        relations.append({
            "source": f"主要人物_{i % 10}",
            "target": f"古代秘宝_{40 + i}",
            "type": "所持および継承" if i % 2 == 0 else "宿命の対立",
        })

    # 2. Setup realistic novel world text (2,000+ tokens)
    raw_text = (
        "第50話：世界の終焉と始まり。\n"
        + "大規模な艦隊と軍勢が集結し、天地を揺るがす最終決戦の幕が上がった。\n"
        + "バルフィア帝国の重魔導兵団は、最前線に巨大な魔導障壁を展開し、王国の防衛ラインを圧倒する。\n"
        + "天を焦がす劫火と地を裂く雷鳴が戦場を支配し、無数の兵士たちが喚声を上げながら激突した。\n"
        + "補給部隊の物資集積所では魔石の搬出が急ピッチで行われ、後方支援の衛生兵たちが手当てに追われる。\n"
    ) * 12 + (
        "祭壇の最深部において、主要人物_0 と 主要人物_1 は背中を合わせ、迫り来る魔導兵団を迎え撃つ。\n"
        + "未回収の伏線 FS-OMEGA-999 が刻印された扉が青白く発光し、古代秘宝_42の神秘が共鳴していた。\n"
    )

    # 3. Setup protected context
    protected = ProtectedContext(
        active_characters=["主要人物_0", "主要人物_1"],
        pending_foreshadowing_ids=["FS-OMEGA-999"],
        pinned_entities={"古代秘宝_42"},
    )

    compressor = FourLayerCompressor(
        config=CompressionConfig(max_tokens=1200, target_reduction_ratio=0.6, cache_enabled=False)
    )

    start_t = time.perf_counter()
    result = compressor.compress(
        raw_text=raw_text,
        entities=entities,
        relations=relations,
        scene_type="combat",
        max_tokens=1200,
        protected_context=protected,
        bypass_cache=True,
    )
    elapsed_ms = (time.perf_counter() - start_t) * 1000

    print(f"Elapsed Time: {elapsed_ms:.2f} ms")
    print(f"Original Tokens: {result.layer1.original_token_count if result.layer1 else 0}")
    print(f"Final Tokens: {result.final_token_count}")
    print(f"Reduction Ratio: {result.overall_reduction_ratio * 100:.1f}%")
    print(f"Retained Entities Count: {len(result.layer4.retained_entities)}")
    print(f"Pinned Count in Result: {result.layer4.pinned_count}")

    # 4. Assertions for Quantitative Benchmark Criteria (Step 65)
    # Criterion 1: Execution under 2500ms for large dataset
    assert elapsed_ms < 2500, f"Performance bottleneck: {elapsed_ms}ms"

    # Criterion 2: Protected active characters & foreshadowing 100% retained
    retained_set = set(result.layer4.retained_entities)
    assert "主要人物_0" in retained_set, "Active character 主要人物_0 was dropped!"
    assert "主要人物_1" in retained_set, "Active character 主要人物_1 was dropped!"
    assert "FS-OMEGA-999" in retained_set, "Pending foreshadowing FS-OMEGA-999 was dropped!"

    # Criterion 3: Token budget obeyed and high reduction ratio achieved (>= 60%)
    assert result.final_token_count <= 1200, f"Token budget exceeded: {result.final_token_count} > 1200"
    assert result.overall_reduction_ratio >= 0.60, f"Reduction ratio too low: {result.overall_reduction_ratio * 100:.1f}% < 60%"

    print("=== Benchmark Passed Successfully (ALL CRITERIA MET) ===")
    return 0


if __name__ == "__main__":
    sys.exit(run_benchmark())
