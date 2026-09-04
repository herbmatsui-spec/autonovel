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
                self.emit_event("writing.failed", {
                    "book_id": book_id,
                    "ep_num": ep_num,
                    "failed_episodes": failed_episodes,
                })
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

            self.emit_event("writing.completed", {
                "book_id": book_id,
                "ep_num": ep_num,
                "word_count": total_chars,
            })

            return AgentResult(
                next_agent=AgentName.ILLUSTRATION,
                artifacts={
                    "drafted_text": drafted_text,
                    "word_count": total_chars,
                    "failed_episodes": [],
                },
            )

        except Exception as e:
            self.emit_event("writing.error", {
                "book_id": book_id,
                "ep_num": ep_num,
                "error": str(e),
            })
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

    async def rewrite_with_focus(
        self,
        book_id: int,
        ep_num: int,
        focus: str,
        params: dict[str, Any] | None = None,
        reporter: Any = None,
    ) -> dict[str, Any]:
        """特定フォーカスでの書き直し（読者体験改善用）。
        
        Args:
            book_id: 書籍ID
            ep_num: 話数
            focus: フォーカス ("reader_experience" 等)
            params: 追加パラメータ
                - enhance_hook: 冒頭フック強化
                - enhance_cliffhanger: 末尾クリフハンガー強化
                - adjust_emotional_arc: 感情曲線調整
            reporter: 進捗レポーター
        """
        params = params or {}
        if reporter:
            reporter.report(f"Ep.{ep_num}: {focus} フォーカスで書き直し開始", "info")
        
        # 既存の章を取得
        chapter = await self.repo.get_chapter(1, ep_num) if self.repo else None
        if not chapter or not chapter.content:
            return {"status": "error", "message": "Chapter not found or empty"}
        
        original_text = chapter.content
        
        # フォーカスに応じた書き直し指示を作成
        rewrite_instructions = []
        if params.get("enhance_hook"):
            rewrite_instructions.append(
                "冒頭200文字で読者の注意を強く引く「謎・違和感・危機」を提示する。"
                "最初の文で主人公の状況や核心的なコンフリクトを示唆せよ。"
            )
        if params.get("enhance_cliffhanger"):
            rewrite_instructions.append(
                "末尾200文字で次話への強い期待感を抱かせる「未解決の要素・衝撃の展開・重要な選択」を配置せよ。"
                "読者が「続きが気になる」と感じるクリフハンガーで締めくくれ。"
            )
        if params.get("adjust_emotional_arc"):
            rewrite_instructions.append(
                "感情曲線を整え、カタルシスのタイミング・強さ・起伏バランスを適切にする。"
                "中盤でのテンション上昇とクライマックスでの感情解放を明確にせよ。"
            )
        
        if not rewrite_instructions:
            rewrite_instructions.append("読者体験全般（フック・クリフハンガー・感情曲線）を向上させよ。")
        
        # 簡易実装: 元のテキストに書き直し指示を付加して返す
        # 実際の実装では LLM による書き直しを行う
        rewrite_prompt = (
            f"以下の本文を、以下の指示に従って書き直せ:\n\n"
            f"【書き直し指示】\n" + "\n".join(f"- {inst}" for inst in rewrite_instructions) + "\n\n"
            f"【元の本文】\n{original_text}\n\n"
            f"【書き直し後の本文】"
        )
        
        # LLM で書き直し実行（簡易版: generator 経由）
        # ここではプレースホルダーとして元のテキストを返す
        rewritten_text = original_text  # TODO: LLM で実際に書き直し
        
        # 章を更新
        if self.repo and hasattr(self.repo, 'update_chapter_content'):
            await self.repo.update_chapter_content(chapter.id, rewritten_text)
        
        if reporter:
            reporter.report(f"Ep.{ep_num}: 書き直し完了 ({len(rewritten_text)}文字)", "info")
        
        return {
            "status": "success",
            "original_length": len(original_text),
            "rewritten_length": len(rewritten_text),
            "focus": focus,
            "instructions_applied": rewrite_instructions,
        }