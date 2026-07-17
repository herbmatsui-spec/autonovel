from typing import Any, Dict

from src.shared.utils import StatusReporter

from .base_workflow import BaseWorkflow


class PlanGenerationWorkflow(BaseWorkflow):
    """企画生成ワークフロー"""
    async def execute(self, reporter: StatusReporter, **kwargs) -> Dict[str, Any]:
        params = kwargs["params"]
        book_id, bible = await self.planner.create_hegemony_plan(
            genre=params.get("genre", "ファンタジー"),
            keywords=params.get("keywords", ""),
            style_key=params.get("style_key", "default"),
            concept=params.get("concept", ""),
            title=params.get("title", ""),
            cheat_scale=params.get("cheat_scale", 3),
            growth_curve=params.get("growth_curve", "最初からカンスト(無双)"),
            system_assist=params.get("system_assist", 50),
            cost_severity=params.get("cost_severity", 3),
            target_eps=params.get("target_eps", 50),
            initial_plot_limit=params.get("initial_limit", 10),
            reporter=reporter,
        )
        return {"book_id": book_id, "title": bible.title}
