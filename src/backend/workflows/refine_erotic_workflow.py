"""
src/backend/workflows/refine_erotic_workflow.py
官能シーン研磨用ワークフロー
"""

from typing import Any, Dict, Optional

from config.erotic_pacing import EroticCurve
from src.shared.utils import StatusReporter

from .base_workflow import BaseWorkflow


class RefineEroticWorkflow(BaseWorkflow):
    """官能シーンの研磨・整合性チェックを行うワークフロー"""

    async def execute(self, reporter: Optional[StatusReporter] = None, **kwargs) -> Dict[str, Any]:
        book_id = kwargs["book_id"]
        ep_num = kwargs["ep_num"]
        intensity = kwargs.get("intensity", 2)
        kwargs.get("platform_preset", "kakuyomu_romance")

        if reporter:
            reporter.set_message("官能研磨を開始中...")
            reporter.add_log(f"対象作品: {book_id}, 話数: {ep_num}, 強度: {intensity}")

        # 1. 該当チャプターの本文を取得
        async with self.repo as uow:
            chapter = await uow.chapters.get_chapter(book_id, ep_num)
            if not chapter:
                raise ValueError(f"Chapter not found for book_id {book_id}, ep_num {ep_num}")

            original_content = chapter.content or ""

            # 2. EroticSpecialist による比喩表現の変換 (metaphor_filter)
            from src.engine.prompts.erotic_specialist import EroticSpecialist

            specialist = EroticSpecialist()
            refined_content = specialist.metaphor_filter(original_content, intensity)

            # 3. 整合性チェック (EroticIntegrityChecker)
            from src.agents.erotic import EroticIntegrityChecker

            checker = EroticIntegrityChecker()
            # 情報から同意状態を取得
            curve = EroticCurve.create_default(intensity)
            peak_beat = curve.get_peak_beat()
            consent_state = peak_beat.consent_state if peak_beat else "implicit"
            is_ok, issues, _, _ = checker.check_all(refined_content, consent_state=consent_state)

            # 3.5. afterglow 品質評価（Peak の後に afterglow がある場合）
            from src.services.erotic_afterglow_evaluator import AfterglowEvaluator

            evaluator = AfterglowEvaluator()
            # afterglow 部分を簡易抽出（最後の 1/4 を afterglow 傾向として評価）
            afterglow_start = len(refined_content) * 3 // 4
            afterglow_candidate = refined_content[afterglow_start:]
            afterglow_ok, afterglow_issues = evaluator.evaluate(afterglow_candidate)

            if reporter:
                if not is_ok:
                    for issue in issues:
                        reporter.add_log(f"⚠️ 整合性警告: {issue}")
                if not afterglow_ok:
                    for issue in afterglow_issues:
                        reporter.add_log(f"⚠️ afterglow品質警告: {issue}")

            # 4. 本文を更新
            chapter.content = refined_content
            # プロット側の erotic_intensity も更新
            plot = await uow.plots.get_plot(book_id, ep_num)
            if plot:
                plot.erotic_intensity = intensity

            await uow.session.commit()

        if reporter:
            reporter.add_log("比喩表現の文学的変換を完了しました")
            if not (is_ok and afterglow_ok):
                if not is_ok:
                    reporter.add_log("整合性チェック警告あり")
                if not afterglow_ok:
                    reporter.add_log("afterglow品質評価警告あり")
            reporter.set_message("官能研磨を完了しました。")

        return {
            "success": True,
            "issues": [],
            "is_ok": is_ok and afterglow_ok,
            "intensity_applied": intensity,
        }
