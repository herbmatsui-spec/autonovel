Created At: 2026-06-01T08:09:18Z
Completed At: 2026-06-01T08:09:18Z
File Path: `file:///i:/%E6%9C%89%E6%96%99%E8%AB%8B%E6%B1%82/R8.4/%E5%80%8B%E4%BA%BA%E9%87%91%E9%8A%AD%E4%B8%80%E8%A6%A7%E8%A1%A8%28%E5%B9%B4%E9%96%93%29%E4%BB%A4%E5%92%8C8%E5%B9%B4%E5%BA%A6/claude2/agents/writing.py`
Total Lines: 831
Total Bytes: 49493
Showing lines 1 to 800
The following code has been modified to include a line number before every line, in the format: <line_number>: <original_line>. Please note that any changes targeting the original code should remove the line number, colon, and leading space.
1: import json
2: import time
3: import random
4: import asyncio
5: import logging
6: from typing import Any, Dict, List, Tuple, Optional
7: from agents.base import BaseAgent
8: from agents.audit import PlotIntegrityMonitor
9: from models import EpisodeDraft, PlotEpisode, extract_int
10: from config import MODEL_WRITING, WRITING_BATCH_SIZE
11: from sanitizer import OutputSanitizer, TonePerfector, ContentValidator
12: from engine_utils import GenreProfile
13: 
14: logger = logging.getLogger(__name__)
15: 
16: class WritingAgent(BaseAgent):
17:     """本文執筆とパイプライン管理を担当"""
18: 
19:     async def generate_episodes(self, book_id: int, start_ep: int, end_ep: int, passion: float, target_word_count: int, do_refine: bool = False, reporter=None, is_easy_mode: bool = False, branch_id: Optional[int] = None, **kwargs) -> int:
20:         if branch_id is None:
21:             book = await self.engine.repo.get_book(book_id)
22:             branch_id = book.current_branch_id if book and book.current_branch_id else 1
23: 
24:         total_eps = end_ep - start_ep + 1
25:         total_len = 0
26:         for i, ep_num in enumerate(range(start_ep, end_ep + 1)):
27:             if reporter and reporter.state.should_stop(): break
28:             
29:             if reporter:
30:                 # 1話ずつの執筆モードでも進捗を表示
31:                 reporter.update_progress(i + 1, total_eps, f"本文執筆中 ({
<truncated 45284 bytes>
(N+1)のプロットを裏で生成開始
731:             await schedule_plot_generation(ep_num + 1)
732: 
733:             # --- STEP 1: 当該話数のプロット完了待機 ---
734:             if ep_num in plot_tasks:
735:                 try:
736:                     await plot_tasks[ep_num]
737:                 except Exception as e:
738:                     logger.error(f"Plot generation task failed for Ep.{ep_num}: {e}", exc_info=True)
739:                     failed_episodes.append({"ep_num": ep_num, "error_message": f"Plot error: {e}"})
740:                     if reporter: reporter.report(f"❌ 第{ep_num}話 プロット生成エラー: {e}", "error")
741:                     break
742: 
743:             plot = await self.engine.repo.get_plot(branch_id, ep_num)
744:             if not plot or not plot.detailed_blueprint:
745:                 # [RECOVERY] If detailed plot is missing (e.g., due to previous API timeouts), try on-demand expansion
746:                 if reporter: reporter.report(f"⚠️ 第{ep_num}話 詳細プロットが未生成です。オンデマンドで復旧を試みます...", "warning")
747:                 try:
748:                     # Synchronous expansion for the missing episode
749:                     await self.engine.planner.expand_plots(
750:                         book_id, [ep_num], arcs, reporter=reporter, branch_id=branch_id
751:                     )
752:                     # Refresh plot data from database
753:                     plot = await self.engine.repo.get_plot(branch_id, ep_num)
754:                 except Exception as e:
755:                     logger.error(f"On-demand plot expansion recovery failed for Ep.{ep_num}: {e}")
756:                 
757:                 if not plot or not plot.detailed_blueprint:
758:                     # Still missing after recovery attempt
759:               
<truncated 2779 bytes>

NOTE: The output was truncated because it was too long. Use a more targeted query or a smaller range to get the information you need.

