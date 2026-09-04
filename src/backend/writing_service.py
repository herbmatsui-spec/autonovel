"""
writing_service.py - WritingService: 本文執筆・研磨を担当するドメインサービス。

UltimateHegemonyEngine の UltimateHegemonyEngine から分離したサービス。
Workflows (EpisodeWritingWorkflow, ChapterImportWorkflow, RetryFailedEpisodesWorkflow,
RefineEroticWorkflow 等) は WritingService を依存対象にし、EngineFacade 経由で
インジェクトされる。

主な責任:
- generate_episodes_pipeline: パイプライン執筆（WritingAgent へ委譲）
- generate_episodes: 単発執筆（WritingAgent へ委譲）
- analyze_and_import_chapter: 手書き原稿インポート（委譲先があれば）
- calculate_book_score: 執筆後の BookScore 計算とフィードバックループ
"""

from typing import Any


class WritingService:
    """覇権小説の本文執筆・研磨を担当するサービス。"""

    def __init__(
        self,
        writer: Any,  # WritingAgent 実体
        repo: Any,  # DataRepository
        pm: Any,  # PromptManager
        style_rag: Any,  # StyleRagManager
        ctx_mgr: Any,  # ContextManager
        reporter_factory: Any,  # StatusReporter 作成用 Callable
        book_score_calculator: Any = None,  # BookScoreCalculator
        score_threshold: float = 70.0,  # 再生成閾値
    ) -> None:
        self.writer = writer
        self.repo = repo
        self.pm = pm
        self.style_rag = style_rag
        self.ctx_mgr = ctx_mgr
        self.reporter_factory = reporter_factory
        self.book_score_calculator = book_score_calculator
        self.score_threshold = score_threshold

    async def generate_episodes_pipeline(
        self,
        book_id: int,
        start_ep: int,
        end_ep: int,
        passion: float,
        target_word_count: int,
        is_easy_mode: bool,
        reporter: Any,
        branch_id: int = 1,
        style_tag: Any = None,
    ) -> tuple[int, list[Any]]:
        """
        エピソード生成パイプラインを実行する。
        実際の実行は writer.generate_episodes_pipeline に委譲。
        """
        return await self.writer.generate_episodes_pipeline(
            book_id=book_id,
            start_ep=start_ep,
            end_ep=end_ep,
            passion=passion,
            target_word_count=target_word_count,
            is_easy_mode=is_easy_mode,
            reporter=reporter,
            branch_id=branch_id,
            style_tag=style_tag,
        )

    async def generate_episodes(
        self,
        book_id: int,
        start_ep: int,
        end_ep: int,
        passion: float,
        target_word_count: int,
        is_easy_mode: bool,
        reporter: Any,
        branch_id: int = 1,
        style_tag: Any = None,
        auto_regenerate: bool = True,  # 自動再生成ループ有効化
        max_retries: int = 3,          # 最大再生成回数
    ) -> int:
        """
        単発のエピソード執筆を実行する。
        実際の実行は writer.generate_episodes に委譲。
        auto_regenerate=True の場合、BookScore 閾値未満で自動再生成ループを実行。
        """
        # 初回執筆
        word_count = await self.writer.generate_episodes(
            book_id=book_id,
            start_ep=start_ep,
            end_ep=end_ep,
            passion=passion,
            target_word_count=target_word_count,
            is_easy_mode=is_easy_mode,
            reporter=reporter,
            branch_id=branch_id,
            style_tag=style_tag,
        )

        if not auto_regenerate or self.book_score_calculator is None:
            return word_count

        # 自動再生成ループ
        for ep in range(start_ep, end_ep + 1):
            for retry in range(max_retries):
                score_result = await self.calculate_book_score(
                    book_id=book_id,
                    chapter_number=ep,
                    genre="",  # TODO: genre を引数で受け取る
                    phase="writing",
                )
                if score_result is None:
                    break
                if not score_result.get("regeneration_triggered", False):
                    if reporter:
                        reporter.report(
                            f"Ep.{ep}: BookScore {score_result['overall_score']:.1f} 達成、再生成不要",
                            "info",
                        )
                    break  # スコア達成

                # 再生成必要
                low_dims = score_result.get("low_dimensions", [])
                actions = score_result.get("regeneration_actions", [])
                if reporter:
                    reporter.report(
                        f"Ep.{ep}: BookScore {score_result['overall_score']:.1f} 閾値未満、"
                        f"再生成 {retry+1}/{max_retries} (低次元: {low_dims})",
                        "warning",
                    )

                # 再生成アクション実行（簡易版: ContextBuilderAgent 等への指示は将来実装）
                # ここでは単純に再執筆をトリガー
                if reporter:
                    for action in actions:
                        reporter.report(
                            f"  再生成アクション: {action['target_agent']}.{action['action']} "
                            f"(focus={action['focus']})",
                            "info",
                        )

                # 再執筆
                word_count = await self.writer.generate_episodes(
                    book_id=book_id,
                    start_ep=ep,
                    end_ep=ep,
                    passion=passion,
                    target_word_count=target_word_count,
                    is_easy_mode=is_easy_mode,
                    reporter=reporter,
                    branch_id=branch_id,
                    style_tag=style_tag,
                )

            # 最大リトライ後も閾値未満の場合
            final_score = await self.calculate_book_score(
                book_id=book_id, chapter_number=ep, phase="writing"
            )
            if final_score and final_score.get("regeneration_triggered"):
                if reporter:
                    reporter.report(
                        f"Ep.{ep}: 最大リトライ({max_retries})到達、スコア {final_score['overall_score']:.1f} で終了",
                        "error",
                    )

        return word_count

    async def calculate_book_score(
        self,
        book_id: int,
        chapter_number: int,
        genre: str = "",
        phase: str = "writing",
    ) -> dict[str, float] | None:
        """執筆完了後の章に対して BookScore を計算し、閾値未満なら再生成トリガーを返す"""
        if self.book_score_calculator is None:
            return None

        from src.agents.orchestrator import AgentContext
        ctx = AgentContext(book_id=book_id, branch_id=1, ep_num=chapter_number, artifacts={})

        score = await self.book_score_calculator.calculate(
            book_id=book_id,
            chapter_number=chapter_number,
            ctx=ctx,
            genre=genre,
            phase=phase,
        )

        result = {
            "overall_score": score.overall_score,
            "structure_score": score.structure_score,
            "coherency_score": score.coherency_score,
            "factual_grounding_score": score.factual_grounding_score,
            "visual_textual_synergy_score": score.visual_textual_synergy_score,
            "reader_experience_score": score.reader_experience_score,
        }

        # 閾値チェック
        if score.overall_score < self.score_threshold:
            result["regeneration_triggered"] = True
            low_dims = self._identify_low_dimensions(score)
            result["low_dimensions"] = low_dims
            # 次元別再生成アクション発行
            result["regeneration_actions"] = self._generate_regeneration_actions(low_dims)
        else:
            result["regeneration_triggered"] = False
            result["regeneration_actions"] = []

        # メトリクス記録
        try:
            from src.backend.observability.metrics import record_book_score
            record_book_score(result, genre, phase)
        except Exception:
            pass  # メトリクス失敗は無視

        return result

    def _identify_low_dimensions(self, score: Any) -> list[str]:
        """閾値未満の次元を特定（簡易実装: 60点未満を低スコアとみなす）"""
        low = []
        if score.structure_score < 60:
            low.append("structure")
        if score.coherency_score < 60:
            low.append("coherency")
        if score.factual_grounding_score < 60:
            low.append("factual_grounding")
        if score.visual_textual_synergy_score < 60:
            low.append("visual_textual_synergy")
        if score.reader_experience_score < 60:
            low.append("reader_experience")
        return low

    def _generate_regeneration_actions(self, low_dimensions: list[str]) -> list[dict[str, Any]]:
        """低スコア次元に対応する再生成アクションを生成"""
        action_map = {
            "structure": {
                "target_agent": "ContextBuilderAgent",
                "action": "rebuild_context_with_focus",
                "focus": "structure",
                "reason": "構造スコア低: アーク境界・テンポ・因果整合性の改善が必要",
                "params": {"enhance_arc_alignment": True, "enhance_pacing": True},
            },
            "coherency": {
                "target_agent": "ContextBuilderAgent",
                "action": "rebuild_context_with_focus",
                "focus": "coherency",
                "reason": "一貫性スコア低: キャラ口調・世界観ルール・固有名詞の統一が必要",
                "params": {"enhance_speech_profiles": True, "enhance_world_rules": True},
            },
            "factual_grounding": {
                "target_agent": "ContextBuilderAgent",
                "action": "rebuild_context_with_focus",
                "focus": "factual_grounding",
                "reason": "事実性スコア低: GraphRAG参照情報・時代考証・用語の整合性改善が必要",
                "params": {"enhance_rag_entities": True, "enhance_historical_accuracy": True},
            },
            "visual_textual_synergy": {
                "target_agent": "IllustrationAgent",
                "action": "regenerate_prompts",
                "focus": "visual_textual_synergy",
                "reason": "視覚×テキスト相乗効果低: 挿絵プロンプトと本文の情報量・焦点・感情トーンの一致改善が必要",
                "params": {"refocus_on_text_entities": True, "match_emotional_tone": True},
            },
            "reader_experience": {
                "target_agent": "WritingAgent",
                "action": "rewrite_with_focus",
                "focus": "reader_experience",
                "reason": "読者体験スコア低: 冒頭フック・末尾クリフハンガー・感情曲線の改善が必要",
                "params": {"enhance_hook": True, "enhance_cliffhanger": True, "adjust_emotional_arc": True},
            },
        }
        actions = []
        for dim in low_dimensions:
            if dim in action_map:
                action = action_map[dim].copy()
                action["dimension"] = dim
                actions.append(action)
        return actions

    async def analyze_and_import_chapter(
        self,
        book_id: int,
        ep_num: int,
        import_text: str,
        do_refine: bool = True,
    ) -> Any:
        """
        手書き原稿のインポート・研磨を実行する。
        writer が analyze_and_import_chapter を持っていれば委譲、
        持っていなければ NotImplementedError を送出（呼び出し側で要ハンドリング）。
        """
        method = getattr(self.writer, "analyze_and_import_chapter", None)
        if method is None:
            raise NotImplementedError(
                "WritingAgent に analyze_and_import_chapter が実装されていません。"
                "ChapterImportWorkflow の実行には当該メソッドが必要です。"
            )
        return await method(
            book_id=book_id,
            ep_num=ep_num,
            import_text=import_text,
            do_refine=do_refine,
        )
