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
    ) -> int:
        """
        単発のエピソード執筆を実行する。
        実際の実行は writer.generate_episodes に委譲。
        """
        return await self.writer.generate_episodes(
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
            result["low_dimensions"] = self._identify_low_dimensions(score)
        else:
            result["regeneration_triggered"] = False

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
