from __future__ import annotations
import json
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING
from engine_agents import PlanningAgent, WritingAgent, MarketingAgent, LogicalAuditor
from background import StatusReporter

if TYPE_CHECKING:
    from engine import UltimateHegemonyEngine, GenerateResult

class HegemonyService:
    """
    アプリケーションサービス層。
    UI(Streamlit)とドメイン(Engine/Agents)の仲介役となり、
    複数のエージェントを跨ぐ複雑なワークフロー（ユースケース）を実装する。
    st.session_state に依存せず、StatusReporter を介して進捗を報告する。
    """
    def __init__(self, engine: "UltimateHegemonyEngine"):
        self.engine = engine

    async def full_auto_workflow(
        self, 
        genre: str, 
        keywords: str, 
        archetype_key: str, 
        target_eps: int, 
        initial_limit: int, 
        word_count: int, 
        reporter: StatusReporter,
        concept: str = "", 
        tone_vibe: float = 0.6, 
    ) -> Dict[str, Any]:
        """かんたんモード: 企画・執筆・パッケージングの一連のフローを実行"""
        from config import STORY_ARCHETYPES
        p_settings = STORY_ARCHETYPES.get(archetype_key, STORY_ARCHETYPES["王道ざまぁ（爽快感最大）"])
        
        reporter.report("🚀 全自動モード開始！", "info")
        
        # 1. 企画生成
        try:
            reporter.update_progress(0, 3, "STEP 1/3: 覇権企画を生成中...")
            book_id, bible = await self.engine.planner.create_hegemony_plan(
                genre=genre,
                keywords=keywords,
                style_key=p_settings.get("style_key", "style_web_standard"),
                concept=concept, # 提案2: コアアイデアを渡す
                title="",
                cheat_scale=p_settings.get("cheat_scale", 4),
                growth_curve=p_settings.get("growth_curve", "最初からカンスト(無双)"),
                system_assist=p_settings.get("system_assist", 70),
                cost_severity=p_settings.get("cost_severity", 2),
                target_eps=target_eps,
                initial_plot_limit=3, # 最初の3話分だけ作り、残りは執筆しながら並列生成して高速化
                reporter=reporter,
            )
            
            # 健全性チェックの実行
            if not await self.engine.planner.audit_bible_completeness(bible, reporter=reporter):
                return {"book_id": book_id, "status": "failed_integrity_check"}

            if reporter.state.should_stop():
                return {"book_id": book_id, "status": "stopped"}
        except Exception as e:
            reporter.report(f"🚨 企画生成中にエラーが発生しました: {e}. APIキーや入力設定を確認してください。", "error")
            raise

        # 2. 並列執筆（プロット生成含む）
        try:
            reporter.update_progress(1, 3, "STEP 2/3: 本文を自動執筆中...")
            # 高速なパイプラインメソッドを使用してプロット生成と執筆をオーバーラップさせ、失敗エピソードも収集
            chars_count, failed_episodes = await self.engine.writer.generate_episodes_pipeline(
                book_id=book_id,
                start_ep=1,
                end_ep=target_eps,
                passion=tone_vibe, # 提案6: トーン/雰囲気スライダーの値をpassionにマッピング
                target_word_count=word_count,
                reporter=reporter,
                is_easy_mode=True
            )
            
            # 自動再試行: 失敗があればもう一度だけスキャンして修復を試みる
            if failed_episodes and not reporter.state.should_stop():
                reporter.report(f"🔄 {len(failed_episodes)}件のエピソードで不備を検知。自動修復中...", "warning")
                retry_chars, still_failed = await self.engine.writer.generate_episodes_pipeline(
                    book_id=book_id,
                    start_ep=1,
                    end_ep=target_eps,
                    passion=tone_vibe,
                    target_word_count=word_count,
                    reporter=reporter,
                    is_easy_mode=True
                )
                chars_count += retry_chars
                failed_episodes = still_failed

            if reporter.state.should_stop():
                return {"book_id": book_id, "status": "stopped"}
        except Exception as e:
            reporter.report(f"🚨 本文執筆中にエラーが発生しました: {e}. プロットやキャラクター設定に問題がないか確認してください。", "error")
            raise

        # 3. 納品パッケージ作成
        try:
            reporter.update_progress(2, 3, "STEP 3/3: 納品パッケージを作成中...")
            zip_data, zip_filename = await self.engine.marketing.create_export_package(book_id)
        except Exception as e:
            reporter.report(f"🚨 納品パッケージ作成中にエラーが発生しました: {e}. 作品データが破損している可能性があります。", "error")
            raise
        
        reporter.update_progress(3, 3, "全行程完了！")
        return {
            "book_id": book_id, 
            "title": bible.title,
            "chars_count": chars_count, 
            "failed_episodes": failed_episodes,
            "zip_data": zip_data, 
            "zip_filename": zip_filename,
        }

    async def plan_generation_workflow(self, params: Dict[str, Any], reporter: StatusReporter) -> Dict[str, Any]:
        """企画生成ワークフロー"""
        book_id, bible = await self.engine.planner.create_hegemony_plan(
            genre=params["genre"],
            keywords=params["keywords"],
            style_key=params["style_key"],
            concept=params.get("concept", ""),
            title=params.get("title", ""),
            cheat_scale=params["cheat_scale"],
            growth_curve=params.get("growth_curve", "最初からカンスト(無双)"),
            system_assist=params["system_assist"],
            cost_severity=params["cost_severity"],
            target_eps=params["target_eps"],
            initial_plot_limit=params["initial_limit"],
            reporter=reporter,
        )
        return {"book_id": book_id, "title": bible.title}

    async def plot_expansion_workflow(self, book_id: int, gen_from: int, gen_to: int, reporter: StatusReporter) -> Dict[str, Any]:
        """プロットの追加・再生成フロー"""
        bible = await self.engine.repo.get_latest_bible(book_id)
        settings = bible.settings if isinstance(bible.settings, dict) else json.loads(bible.settings or "{}") if bible else {}
        arcs = settings.get("arcs", [])
        results = await self.engine.planner.expand_plots(
            book_id, list(range(gen_from, gen_to + 1)), arcs, reporter=reporter
        )
        return {"count": len(results)}

    async def retry_failed_episodes_workflow(
        self, book_id: int, passion: float, word_count: int, reporter: StatusReporter
    ) -> Dict[str, Any]:
        """失敗したエピソードをスキャンし、自動で再試行・修復するバックグラウンドジョブ"""
        book = await self.engine.repo.get_book(book_id)
        target_eps = book.target_eps if book else 50
        chars, failed = await self.engine.writer.generate_episodes_pipeline(
            book_id, 1, target_eps, passion, word_count, reporter=reporter, is_easy_mode=True
        )
        return {"chars_count": chars, "failed_episodes": failed, "book_id": book_id}

    async def episode_writing_workflow(
        self, book_id: int, write_from: int, write_to: int, passion: float, word_count: int, 
        do_refine: bool, env_state: Dict[str, str], pipeline_mode: bool, reporter: StatusReporter
    ) -> Dict[str, Any]:
        """執筆ワークフロー: 通常モードとパイプラインモードの切り替えを隠蔽"""
        # 再試行用に最新のパラメータをセッションへ記録
        import streamlit as st
        st.session_state["last_passion"] = passion
        st.session_state["last_word_count"] = word_count

        if pipeline_mode:
            chars_count, failed = await self.engine.writer.generate_episodes_pipeline(
                book_id, write_from, write_to, passion, word_count, reporter=reporter
            )
            return {"chars_count": chars_count, "failed_episodes": failed, "book_id": book_id}
        else:
            chars_count = await self.engine.writer.generate_episodes(
                book_id, write_from, write_to, passion, word_count, do_refine,
                reporter=reporter, env_state=env_state
            )
            return {"chars_count": chars_count, "book_id": book_id}

    async def plot_rebuild_workflow(
        self,
        params: Dict[str, Any],
        reporter: StatusReporter
    ) -> Dict[str, Any]:
        """プロット再構築ワークフロー: 再構築から詳細展開までを実行"""
        results = await self.engine.planner.rebuild_hegemony_plot(
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

    async def chapter_import_workflow(
        self,
        book_id: int,
        ep_num: int,
        import_text: str,
        do_refine: bool
    ) -> Dict[str, Any]:
        """本文インポートワークフロー"""
        # インポートは比較的短時間だが、品質研磨を含むためサービス化
        result = await self.engine.writer.analyze_and_import_chapter(
            book_id, ep_num, import_text, do_refine=do_refine
        )
        return result

    async def run_critique_optimization_workflow(self, book_id: int, reporter: StatusReporter) -> GenerateResult:
        """エージェントによる自己最適化分析（不一致分析の反復）を実行"""
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