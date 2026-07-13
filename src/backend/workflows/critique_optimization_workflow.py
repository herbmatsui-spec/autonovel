from src.shared.utils import StatusReporter
from src.models.base import GenerateResult

from .base_workflow import BaseWorkflow


class CritiqueOptimizationWorkflow(BaseWorkflow):
    """エージェントによる自己最適化分析（不一致分析の反復）を実行"""
    async def execute(self, reporter: StatusReporter, **kwargs) -> GenerateResult:
        book_id = kwargs["book_id"]
        reporter.report("🕵️ 作品の品質分析とエンジン最適化案の生成を開始します...", "info")
        try:
            result = await self.engine.critique.run_iterative_gap_analysis(book_id)
            if result.success:
                reporter.report("✅ 最適化レポートの生成が完了しました。戦略司令部で結果を確認してください。", "info")
            else:
                reporter.report(f"❌ 分析に失敗しました: {result.error_message}", "error")
            return result
        except Exception as e:
            reporter.report(f"🚨 分析ワークフロー内で予期せぬエラーが発生しました: {str(e)}", "error")
            raise
