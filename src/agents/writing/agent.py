# src/agents/writing/agent.py
"""WritingAgent - 本文生成を担当するスキルエージェント"""
from typing import Any
from src.agents.skill_base import SkillAgent
from src.agents.orchestrator import AgentContext, AgentResult, AgentName


class WritingAgent(SkillAgent):
    """本文生成スキルエージェント"""

    def __init__(
        self,
        repo: Any = None,
        llm: Any = None,
        style_rag: Any = None,
        rag_prefetch: Any = None,
        pm: Any = None,
        ctx_mgr: Any = None,
        reporter_factory: Any = None,
    ):
        super().__init__(repo=repo, llm=llm, style_rag=style_rag, rag_prefetch=rag_prefetch)
        self.pm = pm
        self.ctx_mgr = ctx_mgr
        self.reporter_factory = reporter_factory
        # generator は遅延初期化
        self._generator = None

    def _get_generator(self):
        """Generator 遅延初期化"""
        if self._generator is None:
            from src.agents.writing.generator import WritingGenerator
            self._generator = WritingGenerator(
                repo=self.repo,
                llm=self.llm,
                pm=self.pm,
                style_rag=self.style_rag,
                ctx_mgr=self.ctx_mgr,
                reporter_factory=self.reporter_factory,
            )
        return self._generator

    async def execute(self, ctx: AgentContext) -> AgentResult:
        """スキル実行エントリーポイント"""
        # 必要なパラメータを artifacts から取得
        book_id = ctx.book_id
        branch_id = ctx.branch_id
        ep_num = ctx.ep_num
        artifacts = ctx.artifacts

        start_ep = artifacts.get("start_ep", ep_num)
        end_ep = artifacts.get("end_ep", ep_num)
        passion = artifacts.get("passion", 0.8)
        target_word_count = artifacts.get("target_word_count", 3000)
        is_easy_mode = artifacts.get("is_easy_mode", False)
        reporter = artifacts.get("reporter")
        style_tag = artifacts.get("style_tag")

        # リポーターファクトリからレポーター作成（渡されていない場合）
        if reporter is None and self.reporter_factory:
            reporter = self.reporter_factory(book_id, branch_id)

        generator = self._get_generator()

        try:
            # パイプライン実行
            total_chars, failed_episodes = await generator.generate_episodes_pipeline(
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

            if failed_episodes:
                return AgentResult(
                    next_agent=None,
                    artifacts={
                        "drafted_text": "",
                        "word_count": total_chars,
                        "failed_episodes": failed_episodes,
                    },
                    error=f"Failed episodes: {failed_episodes}",
                )

            # 最後の生成テキストを取得（簡易実装）
            chapter = await self.repo.get_chapter(branch_id, end_ep) if self.repo else None
            drafted_text = chapter.content if chapter else ""

            return AgentResult(
                next_agent=AgentName.ILLUSTRATION,
                artifacts={
                    "drafted_text": drafted_text,
                    "word_count": total_chars,
                    "failed_episodes": [],
                },
            )

        except Exception as e:
            return AgentResult(
                next_agent=None,
                artifacts={},
                error=f"WritingAgent execution failed: {e}",
            )

    # ---- WritingService 互換メソッド（委譲） ----
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
    ) -> tuple[int, list[dict[str, Any]]]:
        """WritingService 互換: パイプライン執筆"""
        generator = self._get_generator()
        return await generator.generate_episodes_pipeline(
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
        """WritingService 互換: 単発執筆"""
        generator = self._get_generator()
        return await generator.generate_episodes(
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

    async def analyze_and_import_chapter(
        self,
        book_id: int,
        ep_num: int,
        import_text: str,
        do_refine: bool = True,
    ) -> Any:
        """WritingService 互換: 原稿インポート（未実装）"""
        raise NotImplementedError("analyze_and_import_chapter is not implemented yet")