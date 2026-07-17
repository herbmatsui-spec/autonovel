from typing import Any, Dict

from src.shared.utils import StatusReporter

from .base_workflow import BaseWorkflow


class PlotRebuildWorkflow(BaseWorkflow):
    """プロット再構築ワークフロー: 再構築から詳細展開までを実行"""
    async def execute(self, reporter: StatusReporter, **kwargs) -> Dict[str, Any]:
        params = kwargs["params"]
        results = await self.planner.rebuild_hegemony_plot(
            book_id=params["book_id"],
            start_ep=params["start_ep"],
            new_total_eps=params["new_total"],
            keywords=params["new_keywords"],
            trend_memo=params["trend_memo"],
            plot_pattern_key=params["plot_pattern"],
            cost_severity=params["cost_severity"],
            cheat_scale=params["cheat_scale"],
            system_assist=params["system_assist"],
            reporter=reporter
        )
        return {"done": True, "count": len(results)}
