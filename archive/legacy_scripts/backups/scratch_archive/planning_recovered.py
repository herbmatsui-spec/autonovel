Created At: 2026-05-30T08:55:43Z
Completed At: 2026-05-30T08:55:44Z
File Path: `file:///i:/%E6%9C%89%E6%96%99%E8%AB%8B%E6%B1%82/R8.4/%E5%80%8B%E4%BA%BA%E9%87%91%E9%8A%AD%E4%B8%80%E8%A6%A7%E8%A1%A8%28%E5%B9%B4%E9%96%93%29%E4%BB%A4%E5%92%8C8%E5%B9%B4%E5%BA%A6/claude2/agents/planning.py`
Total Lines: 1052
Total Bytes: 67014
Showing lines 1 to 800
The following code has been modified to include a line number before every line, in the format: <line_number>: <original_line>. Please note that any changes targeting the original code should remove the line number, colon, and leading space.
1: import json
2: import logging
3: import asyncio
4: from typing import Any, Dict, List, Optional, Tuple
5: from pydantic import ValidationError
6: from agents.base import BaseAgent
7: from models import (
8:     HegemonyAuditResult, WorldRules, CharacterRegistry, WorldBibleCore, 
9:     RoadmapList, ArcList, ArcBlueprint, WorldBible, PlotEpisode, GlobalLogicRepairResult,
10:     EasyModeInferenceResult, UltraFastWorldBible, UltraFastPlotBatch
11: )
12: from config import MODEL_PLANNING, MODEL_PLOT_EXPANSION
13: from engine_utils import safe_model_validate
14: from sanitizer import OutputSanitizer
15: 
16: # [Update: 2026-05-15 16:55 - Cache Busting]
17: logger = logging.getLogger(__name__)
18: 
19: class PlanningAgent(BaseAgent):
20:     """覇権企画の立案と再構築を担当"""
21: 
22:     def _generate_fallback_synopsis(
23:         self,
24:         bible_core: Any,
25:         genre: str,
26:         keywords: str,
27:         engine_key: str
28:     ) -> str:
29:         """
30:         WorldBibleCoreの構成要素（タイトル、コンセプト、主人公、アーク）から、
31:         エンジンキーおよびジャンルに適応した高精細なあらすじを自動合成する。
32:         """
33:         mc_name = (bible_core.mc_profile.name if bible_core.mc_profile else "") or "主人公"
34:         surface = (bible_core.mc_profile.surface_persona if bible_core.mc_profile else "") or "一見平凡な
<truncated 45282 bytes>
line_summary", ""), top_k=3, exclude_chapters=[ep_num])
689:                                 full_context = past_context + "\n" + rag_context
690:                                 
691:                                 from models.beat_sheet import BeatSheet
692:                                 bs_prompt = self.engine.pm.build_beat_sheet_prompt(
693:                                     book.title, ep_num, ep_info, full_context, world_rules=settings
694:                                 )
695:                                 bs_res = await self.engine._generate_json(MODEL_PLOT_EXPANSION, bs_prompt, response_schema=BeatSheet, reporter=reporter)
696:                                 beat_sheet = BeatSheet.model_validate(bs_res.metadata) if bs_res.success else None
697: 
698:                                 if beat_sheet:
699:                                     if reporter: reporter.report(f"⏳ 第{ep_num}話: ビートシートから展開(Expansion)を生成中...", "info")
700:                                     prompt = self.engine.pm.build_expand_from_beats_prompt(
701:                                         book.title, ep_num, beat_sheet, world_rules=settings, current_stress=current_stress
702:                                     )
703:                                     res = await self.engine._generate_json(MODEL_PLOT_EXPANSION, prompt, response_schema=PlotEpisode, expected_ep_num=ep_num, reporter=reporter)
704:                                     if res.success:
705:                                         p_data = PlotEpisode.model_validate(res.metadata)
706:                             
707:                             # フォールバックまたは非階層的生成
708:                             if not p_data:
709:                                 prompt = self.engine.pm.build_plot_expansion_prompt(
710:                                     book.
<truncated 6814 bytes>

NOTE: The output was truncated because it was too long. Use a more targeted query or a smaller range to get the information you need.

