import json
from typing import Any, Dict, List
from models import BookDbModel, ChapterDbModel, PlotDbModel, GenerateResult
from engine_prompts import PromptManager # Import PromptManager
from config import MODEL_PLANNING, MODEL_WRITING, MODEL_PLOT_EXPANSION

class CritiqueAgent:
    """生成された作品を分析し、エンジンの改善案を提案する専用エージェント"""
    def __init__(self, engine):
        self.engine = engine

    async def analyze_work_quality(self, book_id: int) -> str:
        book = await self.engine.repo.get_book(book_id)
        chapters = await self.engine.repo.get_all_non_anchor_chapters(book_id)
        plots = await self.engine.repo.get_all_plots(book_id)

        # 分析用コンテキストの構築
        summary_data = []
        for c in chapters:
            p = next((p for p in plots if p.ep_num == c.ep_num), None)
            summary_data.append({
                "ep": c.ep_num,
                "plot_goal": p.detailed_blueprint if p else "",
                "actual_summary": c.summary,
                "word_count": len(c.content or "")
            })
        
        prompt = self.engine.pm.build_critique_quality_prompt(book.title, json.dumps(summary_data, ensure_ascii=False, indent=2))
        res = await self.engine._generate_json(
            MODEL_PLANNING,
            prompt,
            temp=0.3
        )
        return res.story_content

    async def run_iterative_gap_analysis(self, book_id: int, max_iterations: int = 10) -> GenerateResult:
        """全エピソードの『設計図 vs 本文』を一括で分析し、エンジンの最適化レポートを生成する（APIコールを1回に集約）"""
        book = await self.engine.repo.get_book(book_id)
        chapters = await self.engine.repo.get_all_non_anchor_chapters(book_id)
        plots = await self.engine.repo.get_all_plots(book_id)

        if not chapters:
            return GenerateResult(success=False, error_message="分析対象のチャプターが存在しません。")

        # 分析対象を最大10エピソードに制限
        target_chapters = chapters[:max_iterations]
        
        # 一括分析用のバッチコンテキストを構築
        batch_data = []
        for ch in target_chapters:
            plot = next((p for p in plots if p.ep_num == ch.ep_num), None)
            if not plot: continue
            
            batch_data.append(
                f"--- 第{ch.ep_num}話 分析データ ---\n"
                f"【プロット設計図】: {plot.detailed_blueprint}\n"
                f"【実際の執筆本文(抜粋)】: {ch.content[:1500]}...\n"
            )

        batch_analysis_prompt = self.engine.pm.build_iterative_gap_analysis_prompt(book.genre, book.title, "\n\n".join(batch_data))
        res = await self.engine._generate_json(
            MODEL_PLANNING,
            batch_analysis_prompt,
            temp=0.3
        )
        if res.success:
            await self.engine.repo.save_optimization_report(book_id, res.metadata)
        return res

    async def run_dry_run(self, book_id: int, ep_num: int, improved_prompt: str) -> str:
        """提案されたプロンプトを使用して、特定のシーンを再生成して比較する"""
        plot = await self.engine.repo.get_plot(book_id, ep_num)
        if not plot: return "対象話数が見つかりません。"

        # 既存のプロンプト構築に、強制力のある一文を注入
        prompt = self.engine.pm.build_dry_run_prompt(ep_num, improved_prompt, plot.detailed_blueprint, plot.script_content)
        res = await self.engine._generate_json(
            MODEL_WRITING, # ドライランは執筆モデルで実行
            prompt,
            temp=0.7
        )
        return res.story_content