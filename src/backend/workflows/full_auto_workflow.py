from typing import Any, Dict

from src.shared.utils import StatusReporter

from ._shared_ops import run_pipeline_with_retry
from .base_workflow import BaseWorkflow


class FullAutoWorkflow(BaseWorkflow):
    """かんたんモード: 企画・執筆・パッケージングの一連のフローを実行"""
    async def execute(self, reporter: StatusReporter, **kwargs) -> Dict[str, Any]:
        genre = kwargs["genre"]
        keywords = kwargs["keywords"]
        archetype_key = kwargs["archetype_key"]
        target_eps = kwargs["target_eps"]
        initial_limit = kwargs["initial_limit"]
        word_count = kwargs["word_count"]
        concept = kwargs.get("concept", "")
        tone_vibe = kwargs.get("tone_vibe", 0.6)

        from config import STORY_ARCHETYPES, resolve_archetype_key
        archetype_key = resolve_archetype_key(archetype_key)
        p_settings = STORY_ARCHETYPES.get(archetype_key, STORY_ARCHETYPES["王道ざまぁ（爽快感最大）"])

        reporter.report("🚀 全自動モード開始！", "info")

        # 1. 企画生成
        try:
            reporter.update_progress(0, 3, "STEP 1/3: 覇権企画を生成中...")
            book_id, bible = await self.engine.planner.create_hegemony_plan(
                genre=genre,
                keywords=keywords,
                style_key=p_settings.get("style_key", "style_web_standard"),
                concept=concept,
                title="",
                cheat_scale=p_settings.get("cheat_scale", 4),
                growth_curve=p_settings.get("growth_curve", "最初からカンスト(無双)"),
                system_assist=p_settings.get("system_assist", 70),
                cost_severity=p_settings.get("cost_severity", 2),
                target_eps=target_eps,
                initial_plot_limit=3,
                reporter=reporter,
            )
            
            # P1-15: カタルシスパターン自動生成
            try:
                from src.backend.engine_narrative import WavePatternAnalyzer
                from config.project_context import ProjectContext
                
                # tension履歴を取得（初期プロット用）
                plots = await self.engine.repo.plot.get_all_plots(book_id)
                tension_history = [getattr(p, "tension", 50) for p in plots] if plots else [50] * 5
                
                # WavePatternAnalyzerでパターン分析
                wave_analyzer = WavePatternAnalyzer(
                    threshold=ProjectContext.get_setting("catharsis_threshold", 65),
                    reset_value=ProjectContext.get_setting("catharsis_reset_value", 0),
                )
                catharsis_pattern = wave_analyzer.analyze(tension_history)
                
                # bibleにカタルシスパターン情報を追加（拡張フィールドとして保存）
                if hasattr(bible, 'model_dump'):
                    bible_dict = bible.model_dump()
                else:
                    bible_dict = dict(bible) if not isinstance(bible, dict) else bible
                
                bible_dict['catharsis_pattern'] = catharsis_pattern.model_dump()
                bible_dict['catharsis_positions'] = catharsis_pattern.catharsis_points
                
                # もしbibleがPydanticモデルなら更新、dictならそのまま使う
                if hasattr(bible, 'model_copy'):
                    bible = bible.model_copy(update=bible_dict)
                elif isinstance(bible, dict):
                    bible.update(bible_dict)
                    
                reporter.report(f"📊 カタルシスパターン分析完了: {len(catharsis_pattern.catharsis_points)}個のカタルシス点を検出", "info")
            except Exception as e:
                reporter.report(f"⚠️ カタルシスパターン分析中にエラーが発生しましたが、処理を継続します: {e}", "warning")
            
            # 健全性チェックの実行
            if hasattr(self.engine.planner, "plan_auditor") and self.engine.planner.plan_auditor and not await self.engine.planner.plan_auditor.audit_bible_completeness(bible, reporter=reporter):
                return {"book_id": book_id, "status": "failed_integrity_check"}

            if reporter.state.should_stop():
                return {"book_id": book_id, "status": "stopped"}
        except Exception as e:
            reporter.report(f"🚨 企画生成中にエラーが発生しました: {e}. APIキーや入力設定を確認してください。", "error")
            raise e

        # 2. 並列執筆（プロット生成含む）
        try:
            reporter.update_progress(1, 3, "STEP 2/3: 本文を自動執筆中...")
            chars_count, failed_episodes = await run_pipeline_with_retry(
                writer=self.engine.writer,
                book_id=book_id,
                start_ep=1,
                end_ep=target_eps,
                passion=tone_vibe,
                word_count=word_count,
                reporter=reporter,
                is_easy_mode=True,
                max_retries=1
            )

            if reporter.state.should_stop():
                return {"book_id": book_id, "status": "stopped"}
        except Exception as e:
            reporter.report(f"🚨 本文執筆中にエラーが発生しました: {e}. プロットやキャラクター設定に問題がないか確認してください。", "error")
            raise e

        # 3. 納品パッケージ作成
        try:
            reporter.update_progress(2, 3, "STEP 3/3: 納品パッケージを作成中...")
            zip_data, zip_filename = None, f"export_{book_id}.zip"
        except Exception as e:
            reporter.report(f"🚨 納品パッケージ作成中にエラーが発生しました: {e}. 作品データが破損している可能性があります。", "error")
            raise e

        book = await self.engine.repo.get_book(book_id)
        actual_title = book.title if book else "名称未設定"

        reporter.update_progress(3, 3, "全行程完了！")
        return {
            "book_id": book_id,
            "title": actual_title,
            "chars_count": chars_count,
            "failed_episodes": failed_episodes,
            "zip_data": zip_data,
            "zip_filename": zip_filename,
        }
