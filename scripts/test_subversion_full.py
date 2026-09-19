# scripts/test_subversion_full.py
import sys
import asyncio
sys.path.insert(0, '.')

from unittest.mock import AsyncMock, MagicMock
from src.agents.planning import PlanningAgent

async def main():
    # モックLLMで高速実行
    llm = MagicMock()
    
    # Arc generation response
    arc_response = {
        "success": True,
        "metadata": {
            "arcs": [
                {"arc_num": 1, "start_ep": 1, "end_ep": 15, "title": "第1章", "summary": "追放から覚醒へ"},
                {"arc_num": 2, "start_ep": 16, "end_ep": 30, "title": "第2章", "summary": "復讐の道"},
                {"arc_num": 3, "start_ep": 31, "end_ep": 40, "title": "第3章", "summary": "最終決戦"},
            ]
        }
    }
    
    # Beat sheet response
    beat_response = {
        "success": True,
        "data": "\n".join([
            f"{ep},フェーズ,ミッション,{0.5 + ep*0.01},シーン{ep}"
            for ep in range(1, 41)
        ])
    }
    
    # Use side_effect with enough responses for multiple calls
    call_count = [0]
    def mock_generate_json(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] % 2 == 1:
            return arc_response
        else:
            return beat_response
    
    llm.generate_json = AsyncMock(side_effect=mock_generate_json)
    
    pm = MagicMock()
    pm.build_arc_generation_prompt.return_value = "prompt"
    pm.render_async = AsyncMock(return_value="prompt")
    
    agent = PlanningAgent(llm=llm, prompt_manager=pm)
    
    print("=" * 60)
    print("Testing generate_arcs with subversion")
    print("=" * 60)
    
    arcs = await agent.generate_arcs(
        "Test Novel", 
        "Hero exiled, gets cheat power", 
        40,
        subversion_enabled=True, 
        subversion_interval=3
    )
    print(f"Arcs: {len(arcs.arcs)}")
    for arc in arcs.arcs:
        if hasattr(arc, "subversion") and arc.subversion:
            print(f"  Arc{arc.arc_num} Ep{arc.subversion.trigger_ep}: {arc.subversion.pattern_type}")
        if arc.thematic_milestone:
            print(f"  Arc{arc.arc_num} milestone: {arc.thematic_milestone[:60]}...")
    
    print()
    print("=" * 60)
    print("Testing generate_commercial_beat_sheet with subversion")
    print("=" * 60)
    
    beats = await agent.generate_commercial_beat_sheet(
        "Test Novel", 
        "Synopsis", 
        subversion_enabled=True
    )
    sub_beats = [b for b in beats if "裏切り" in b.mission]
    print(f"Total beats: {len(beats)}")
    print(f"Subversion beats: {len(sub_beats)}")
    for b in sub_beats:
        print(f"  Ep{b.ep_num}: {b.mission[:50]}... (tension: {b.tension_target})")
    
    print()
    print("=" * 60)
    print("Testing execute() with subversion_engine in artifacts")
    print("=" * 60)
    
    ctx = MagicMock()
    ctx.book_id = "test_book"
    ctx.artifacts = {
        "title": "Test Novel",
        "synopsis": "Hero exiled, gets cheat power",
        "target_eps": 40,
        "start_ep": 1,
        "subversion_enabled": True,
        "subversion_interval": 3,
    }
    
    result = await agent.execute(ctx)
    
    print(f"Artifacts keys: {list(result.artifacts.keys())}")
    if "subversion_engine" in result.artifacts:
        engine_data = result.artifacts["subversion_engine"]
        print(f"Subversion engine schedule: {len(engine_data.get('schedule', []))} entries")
        for entry in engine_data.get('schedule', [])[:5]:
            print(f"  Ep{entry['trigger_ep']}: {entry['pattern_type']}")
        if len(engine_data.get('schedule', [])) > 5:
            print(f"  ... and {len(engine_data['schedule']) - 5} more")
    
    print()
    print("=" * 60)
    print("Testing disabled mode")
    print("=" * 60)
    
    arcs_disabled = await agent.generate_arcs(
        "Test Novel", 
        "Synopsis", 
        10,
        subversion_enabled=False
    )
    has_subversion = any("裏切り" in getattr(arc, "thematic_milestone", "") for arc in arcs_disabled.arcs)
    print(f"Subversion disabled - has subversion in arcs: {has_subversion}")
    assert not has_subversion, "Should not have subversion when disabled"
    print("OK: Disabled mode works correctly")
    
    print()
    print("=" * 60)
    print("ALL TESTS PASSED!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())