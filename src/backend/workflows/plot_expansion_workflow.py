import json
from typing import Any, Dict

from src.shared.utils import StatusReporter

from .base_workflow import BaseWorkflow


class PlotExpansionWorkflow(BaseWorkflow):
    """プロットの追加・再生成フロー"""
    async def execute(self, reporter: StatusReporter, **kwargs) -> Dict[str, Any]:
        book_id = kwargs["book_id"]
        gen_from = kwargs["gen_from"]
        gen_to = kwargs["gen_to"]
        mode = kwargs.get("mode", "final")

        bible = await self.repo.get_latest_bible(book_id)
        print(f"DEBUG bible={bible!r}, settings={getattr(bible, \"settings\", None)!r}")
        settings = bible.settings if isinstance(bible.settings, dict) else json.loads(bible.settings or "{}") if bible else {}
        arcs = settings.get("arcs", [])
        # 候補生成モードの場合、planner側に候補生成を指示する
        # 現在の expand_plots が candidates をサポートしていない場合は、
        # planner 内部の LLM 呼び出しで divergence_instruction が注入されるため、
        # その結果をそのまま保存する。
        # 1. 生成前に目標Tension値を計算してDBに保存
        #- ジャンルと物語タイプをBibleから取得（簡易的に'general'と想定）
        genre = "general"
        story_type = None
        for ep_num in range(gen_from, gen_to + 1):
            await self.determine_target_tension(book_id, ep_num, genre, story_type)

        # 2. プロット展開を実行
        results = await self.planner.expand_plots(
            book_id, list(range(gen_from, gen_to + 1)), arcs, reporter=reporter,
            force=True if mode == "candidates" else False
        )

        # 3. 生成されたTension値のバリデーション
        if results and mode != "candidates":
            for res in results:
                ep_num = res.ep_num
                gen_tension = res.tension / 100.0 # 0-100 scale to 0.0-1.0
                is_valid, dev = await self.validate_tension_deviation(ep_num, gen_tension, book_id)
                if not is_valid:
                    if reporter:
                        reporter.report(f"第{ep_num}話のTensionが目標から逸脱しています (偏差: {dev:.2f})。次回の調整を推奨します。", "warn")
        return {"count": len(results), "mode": mode}
