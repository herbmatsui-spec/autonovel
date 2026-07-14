"""
src/backend/workflows/refine_erotic_workflow.py
螳倩・繧ｷ繝ｼ繝ｳ遐皮｣ｨ逕ｨ繝ｯ繝ｼ繧ｯ繝輔Ο繝ｼ
"""
from typing import Any, Dict, Optional

from config.erotic_pacing import EroticCurve
from src.shared.utils import StatusReporter

from .base_workflow import BaseWorkflow


class RefineEroticWorkflow(BaseWorkflow):
    """螳倩・繧ｷ繝ｼ繝ｳ縺ｮ遐皮｣ｨ繝ｻ謨ｴ蜷域ｧ繝√ぉ繝・け繧定｡後≧繝ｯ繝ｼ繧ｯ繝輔Ο繝�"""
    async def execute(self, reporter: Optional[StatusReporter] = None, **kwargs) -> Dict[str, Any]:
        book_id = kwargs["book_id"]
        ep_num = kwargs["ep_num"]
        intensity = kwargs.get("intensity", 2)
        platform_preset = kwargs.get("platform_preset", "kakuyomu_romance")

        if reporter:
            reporter.set_message("螳倩・遐皮｣ｨ繧帝幕蟋倶ｸｭ...")
            reporter.add_log(f"蟇ｾ雎｡菴懷刀: {book_id}, 隧ｱ謨ｰ: {ep_num}, 蠑ｷ蠎ｦ: {intensity}")

        # 1. 隧ｲ蠖薙メ繝｣繝励ち繝ｼ縺ｮ譛ｬ譁・ｒ蜿門ｾ・
        async with self.engine.repo as uow:
            chapter = await uow.chapters.get_chapter(book_id, ep_num)
            if not chapter:
                raise ValueError(f"Chapter not found for book_id {book_id}, ep_num {ep_num}")

            original_content = chapter.content or ""

            # 2. EroticSpecialist 縺ｫ繧医ｋ豈泌湊陦ｨ迴ｾ縺ｮ螟画鋤 (metaphor_filter)
            from src.engine.prompts.erotic_specialist import EroticSpecialist
            specialist = EroticSpecialist()
            refined_content = specialist.metaphor_filter(original_content, intensity)

            # 3. 謨ｴ蜷域ｧ繝√ぉ繝・け (EroticIntegrityChecker)
            from src.agents.erotic_integrity import EroticIntegrityChecker
            checker = EroticIntegrityChecker()
            # 情報から同意状態を取得
            curve = EroticCurve.create_default(intensity)
            peak_beat = curve.get_peak_beat()
            consent_state = peak_beat.consent_state if peak_beat else "implicit"
            is_ok, issues, _, _ = checker.check_all(refined_content, consent_state=consent_state)

            # 3.5. afterglow 蜩∬ｳｪ隧穂ｾ｡・・eak 縺ｮ蠕後↓ afterglow 縺後≠繧句ｴ蜷茨ｼ・
            from src.services.erotic_afterglow_evaluator import AfterglowEvaluator
            evaluator = AfterglowEvaluator()
            # afterglow 驛ｨ蛻・ｒ邁｡譏捺歓蜃ｺ・域怙蠕後・ 1/4 繧・afterglow 蛯ｾ蜷代→縺励※隧穂ｾ｡・・
            afterglow_start = len(refined_content) * 3 // 4
            afterglow_candidate = refined_content[afterglow_start:]
            afterglow_ok, afterglow_issues = evaluator.evaluate(afterglow_candidate)

            # (existing謨ｴ蜷域ｧ繝√ぉ繝・け驛ｨ蛻・弍逵∫払...)
            if not is_ok:
                for issue in issues:
                    reporter.add_log(f"笞・・謨ｴ蜷域ｧ隴ｦ蜻・ {issue}")
            if not afterglow_ok:
                for issue in afterglow_issues:
                    reporter.add_log(f"笞・・afterglow蜩∬ｳｪ隴ｦ蜻・ {issue}")

            # 4. 譛ｬ譁・ｒ譖ｴ譁ｰ
            chapter.content = refined_content
            # 繝励Ο繝・ヨ蛛ｴ縺ｮ erotic_intensity 繧よ峩譁ｰ
            plot = await uow.plots.get_plot(book_id, ep_num)
            if plot:
                plot.erotic_intensity = intensity

            await uow.session.commit()

        if reporter:
            reporter.add_log("豈泌湊陦ｨ迴ｾ縺ｮ譁・ｭｦ逧・､画鋤繧貞ｮ御ｺ・＠縺ｾ縺励◆")
            if not (is_ok and afterglow_ok):
                if not is_ok:
                    reporter.add_log("謨ｴ蜷域ｧ繝√ぉ繝・け縺失敗")
                if not afterglow_ok:
                    reporter.add_log("afterglow蜩∬ｳｪ隧穂ｾ｡繝√ぉ繝・け縺失敗")
            reporter.set_message("螳倩・遐皮｣ｨ繧貞ｮ御ｺ・＠縺ｾ縺励◆縲・")

        return {
            "success": True,
            "issues": [],
            "is_ok": is_ok and afterglow_ok,
            "intensity_applied": intensity
        }
