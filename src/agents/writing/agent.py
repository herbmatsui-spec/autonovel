# src/agents/writing/agent.py
"""WritingAgent - 本文生成を担当するスキルエージェント"""
import logging
from typing import Any
from src.agents.skill_base import SkillAgent
from src.agents.orchestrator import AgentContext, AgentResult, AgentName

logger = logging.getLogger(__name__)


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
        book_id: int = ctx.book_id
        branch_id: int = ctx.branch_id
        ep_num: int = ctx.ep_num
        artifacts: dict[str, Any] = ctx.artifacts

        start_ep: int = artifacts.get("start_ep", ep_num)
        end_ep: int = artifacts.get("end_ep", ep_num)
        passion: float = artifacts.get("passion", 0.8)
        target_word_count: int = artifacts.get("target_word_count", 3000)
        is_easy_mode: bool = artifacts.get("is_easy_mode", False)
        reporter: Any = artifacts.get("reporter")
        style_tag: Any = artifacts.get("style_tag")

        # 再生成フォーカス取得（WritingService からの指示）
        regeneration_focus: list[str] = artifacts.get("regeneration_focus", [])
        regeneration_action: Any = artifacts.get("regeneration_action")
         
        # 検出: AuditAggregatorNode からの再生成ディレクティブ (regeneration_directive)
        regeneration_directive: Any = artifacts.get("regeneration_directive")
        if regeneration_directive:
            ctx.artifacts["regeneration_mode"] = True
            ctx.artifacts["regeneration_directive"] = regeneration_directive
            logger.info(f"WritingAgent: 再生成モード検出 - directive found, length={len(regeneration_directive)}")

        if regeneration_focus:
            ctx.artifacts["regeneration_mode"] = True
            ctx.artifacts["regeneration_focus"] = regeneration_focus
            if regeneration_action:
                ctx.artifacts["writing_focus"] = regeneration_action.writing_focus
            logger.info(f"WritingAgent: 再生成モード - focus={regeneration_focus}")

        # リポーターファクトリからレポーター作成（渡されていない場合）
        reporter = artifacts.get("reporter")
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
                regeneration_focus=artifacts.get("regeneration_focus", []),
                writing_focus=artifacts.get("writing_focus", []),
                regeneration_directive=artifacts.get("regeneration_directive"),
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
            drafted_text: str = chapter.content if chapter else ""

            self.emit_event("writing.completed", {
                "book_id": book_id,
                "ep_num": ep_num,
                "word_count": total_chars,
            })

            return AgentResult(
                next_agent=AgentName.ENRICHMENT,
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

    # ---- WritingService 互換メソッド（委託） ----
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
        regeneration_focus: list[str] | None = None,
        writing_focus: list[str] | None = None,
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
            regeneration_focus=regeneration_focus or [],
            writing_focus=writing_focus or [],
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
        regeneration_focus: list[str] | None = None,
        writing_focus: list[str] | None = None,
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
            regeneration_focus=regeneration_focus or [],
            writing_focus=writing_focus or [],
        )

    async def analyze_and_import_chapter(
        self,
        book_id: int,
        ep_num: int,
        import_text: str,
        do_refine: bool = True,
    ) -> int:
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
        
        # Actionable Diff などの追加指示があれば反映
        actionable_diffs = params.get("actionable_diffs", [])
        if actionable_diffs:
            for diff in actionable_diffs:
                if isinstance(diff, dict):
                    loc = diff.get("location", "")
                    orig = diff.get("original_quote", "")
                    sug = diff.get("improved_suggestion", "")
                    rat = diff.get("rationale", "")
                    diff_line = f"【修正箇所: {loc}】原文「{orig}」→ 改善案「{sug}」 (理由: {rat})"
                    rewrite_instructions.append(diff_line)
                elif hasattr(diff, "improved_suggestion"):
                    diff_line = f"【修正箇所: {getattr(diff, 'location', '')}】改善案「{getattr(diff, 'improved_suggestion', '')}」 (理由: {getattr(diff, 'rationale', '')})"
                    rewrite_instructions.append(diff_line)

        if not rewrite_instructions:
            rewrite_instructions.append("読者体験全般（フック・クリフハンガー・感情曲線）を向上させよ。")

        rewrite_prompt = (
            f"あなたはプロのWeb小説作家兼編集者です。以下の本文を、指定された【書き直し指示】に従って推敲・改稿してください。\n\n"
            f"【書き直し指示】\n" + "\n".join(f"- {inst}" for inst in rewrite_instructions) + "\n\n"
            f"【制約事項】\n"
            f"- 前置きや解説（「はい」「以下が書き直しです」等）は一切出力せず、改稿後の小説本文のみを出力すること。\n"
            f"- 視点（一人称/三人称）や文体、登場人物の口調の一貫性を保つこと。\n\n"
            f"【元の本文】\n{original_text}\n\n"
            f"【改稿後の本文】"
        )

        import inspect
        import time
        start_time = time.perf_counter()

        # LLM で書き直し実行
        rewritten_text = ""
        if self.llm is not None:
            try:
                if hasattr(self.llm, "generate_text"):
                    res = self.llm.generate_text(
                        prompt=rewrite_prompt,
                        system_prompt="プロの小説家として、指示に従い本文を魅力的に改稿してください。解説や挨拶は含めず本文のみを出力してください。",
                        max_tokens=max(2000, int(len(original_text) * 1.5)),
                    )
                    if inspect.isawaitable(res):
                        rewritten_text = await res
                    else:
                        rewritten_text = str(res)
                elif hasattr(self.llm, "generate"):
                    res = self.llm.generate(rewrite_prompt)
                    if inspect.isawaitable(res):
                        rewritten_text = await res
                    else:
                        rewritten_text = str(res)
            except Exception as llm_err:
                logger.warning(f"WritingAgent rewrite LLM error: {llm_err}")

        # 出力テキストのサニタイズ（AI前置き・コードブロック等の除去）
        if rewritten_text:
            try:
                from src.backend.sanitizer import TextFormatter
                rewritten_text = TextFormatter.remove_ai_isms(rewritten_text).strip()
            except Exception:
                pass
        else:
            rewritten_text = original_text

        exec_time_ms = int((time.perf_counter() - start_time) * 1000)

        # 変化率の計算
        orig_len = len(original_text)
        rewritten_len = len(rewritten_text)
        diff_ratio = abs(rewritten_len - orig_len) / max(1, orig_len)

        # 章を更新
        if self.repo and hasattr(self.repo, 'update_chapter_content'):
            res = self.repo.update_chapter_content(chapter.id, rewritten_text)
            if inspect.isawaitable(res):
                await res

        if reporter:
            reporter.report(f"Ep.{ep_num}: 書き直し完了 ({orig_len}字 → {rewritten_len}字)", "info")

        return {
            "status": "success",
            "original_length": orig_len,
            "rewritten_length": rewritten_len,
            "diff_ratio": round(diff_ratio, 4),
            "execution_time_ms": exec_time_ms,
            "focus": focus,
            "instructions_applied": rewrite_instructions,
            "rewritten_text": rewritten_text,
        }

    async def rewrite_for_dimension(
        self,
        book_id: int,
        branch_id: int,
        ep_num: int,
        dimension: str,
        actionable_diffs: list[dict[str, Any]] | None = None,
        reporter: Any = None,
    ) -> dict[str, Any]:
        """PDCA用: 特定ディメンションに特化した書き直しを行う。

        Args:
            book_id: 書籍ID
            branch_id: ブランチID
            ep_num: 話数
            dimension: 改善ディメンション
                - "reader_experience": 読者体験全般
                - "catharsis": カタルシス強化
                - "tension": テンション・テンポ
                - "hook": 冒頭フック強化
                - "cliffhanger": クリフハンガー強化
                - "emotional_arc": 感情曲線調整
            actionable_diffs: ActionableDiffリスト
                各要素: {"location": str, "original_quote": str, "improved_suggestion": str, "rationale": str}
            reporter: 進捗レポーター
        """
        import time
        import inspect

        start_time = time.perf_counter()

        if reporter:
            reporter.report(f"Ep.{ep_num}: {dimension} ディメンションで書き直し開始", "info")

        # 既存の章を取得
        chapter = await self.repo.get_chapter(branch_id, ep_num) if self.repo else None
        if not chapter or not chapter.content:
            return {"status": "error", "message": "Chapter not found or empty"}

        original_text = chapter.content

        # ディメンションに応じた書き直し指示を作成
        dimension_instructions = {
            "reader_experience": "読者体験全般（フック・クリフハンガー・感情曲線）を向上させよ。冒頭で謎・違和感・危機を提示し、中盤でテンションを上げ、クライマックスで感情解放を明確にする。末尾には未解決の要素や衝撃の展開を配置し、次話への期待感を抱かせるクリフハンガーで締めくくれ。",
            "catharsis": "カタルシス（感情解放）のタイミング・強さ・起伏バランスを最適化せよ。中盤でのテンション上昇とクライマックスでの感情解放を明確にし、読者に強いカタルシスを与える構成にせよ。燃やすコスト（犠牲・喪失）と得られる報酬（報酬・解放）のバランスを調整せよ。",
            "tension": "テンション・テンポのバランスを整えよ。序盤から中盤にかけて緩やかにテンションを上げ、クライマックス直前で最大に達し、カタルシス後に適切に下げる。章全体のペーシング（起承転結のテンポ）を見直し、緩急を明確にせよ。",
            "hook": "冒頭200文字で読者の注意を強く引く「謎・違和感・危機」を提示せよ。最初の文で主人公の状況や核心的なコンフリクトを示唆し、読者が「何が起こるのか」と知りたくなるフックを作れ。",
            "cliffhanger": "末尾200文字で次話への強い期待感を抱かせる「未解決の要素・衝撃の展開・重要な選択」を配置せよ。読者が「続きが気になる」と感じるクリフハンガーで締めくくれ。未解決の謎、衝撃の真相、主人公の重大な選択のいずれかを提示せよ。",
            "emotional_arc": "感情曲線を整え、カタルシスのタイミング・強さ・起伏バランスを適切にする。中盤でのテンション上昇とクライマックスでの感情解放を明確にし、主人公の内面変化（恐怖→決意、不安→覚悟等）を丁寧に描写せよ。",
        }

        base_instruction = dimension_instructions.get(
            dimension,
            "読者体験全般（フック・クリフハンガー・感情曲線）を向上させよ。",
        )

        rewrite_instructions = [base_instruction]

        # Actionable Diff があれば反映
        if actionable_diffs:
            for diff in actionable_diffs:
                if isinstance(diff, dict):
                    loc = diff.get("location", "")
                    orig = diff.get("original_quote", "")
                    sug = diff.get("improved_suggestion", "")
                    rat = diff.get("rationale", "")
                    diff_line = f"【修正箇所: {loc}】原文「{orig}」→ 改善案「{sug}」 (理由: {rat})"
                    rewrite_instructions.append(diff_line)
                elif hasattr(diff, "improved_suggestion"):
                    diff_line = f"【修正箇所: {getattr(diff, 'location', '')}】改善案「{getattr(diff, 'improved_suggestion', '')}」 (理由: {getattr(diff, 'rationale', '')})"
                    rewrite_instructions.append(diff_line)

        rewrite_prompt = (
            f"あなたはプロのWeb小説作家兼編集者です。以下の本文を、指定された【書き直し指示】に従って推敲・改稿してください。\n\n"
            f"【書き直し指示】\n" + "\n".join(f"- {inst}" for inst in rewrite_instructions) + "\n\n"
            f"【制約事項】\n"
            f"- 前置きや解説（「はい」「以下が書き直しです」等）は一切出力せず、改稿後の小説本文のみを出力すること。\n"
            f"- 視点（一人称/三人称）や文体、登場人物の口調の一貫性を保つこと。\n\n"
            f"【元の本文】\n{original_text}\n\n"
            f"【改稿後の本文】"
        )

        start_time = time.perf_counter()
        rewritten_text = ""

        if self.llm is not None:
            try:
                import inspect as inspect_mod
                if hasattr(self.llm, "generate_text"):
                    res = self.llm.generate_text(
                        prompt=rewrite_prompt,
                        system_prompt="プロの小説家として、指示に従い本文を魅力的に改稿してください。解説や挨拶は含めず本文のみを出力してください。",
                        max_tokens=max(2000, int(len(original_text) * 1.5)),
                    )
                    if inspect_mod.isawaitable(res):
                        rewritten_text = await res
                    else:
                        rewritten_text = str(res)
                elif hasattr(self.llm, "generate"):
                    res = self.llm.generate(rewrite_prompt)
                    if inspect_mod.isawaitable(res):
                        rewritten_text = await res
                    else:
                        rewritten_text = str(res)
            except Exception as llm_err:
                logger.warning(f"WritingAgent rewrite_for_dimension LLM error: {llm_err}")

        # 出力テキストのサニタイズ（AI前置き・コードブロック等の除去）
        if rewritten_text:
            try:
                from src.backend.sanitizer import TextFormatter
                rewritten_text = TextFormatter.remove_ai_isms(rewritten_text).strip()
            except Exception:
                pass
        else:
            rewritten_text = original_text

        exec_time_ms = int((time.perf_counter() - start_time) * 1000)

        # 変化率の計算
        orig_len = len(original_text)
        rewritten_len = len(rewritten_text)
        diff_ratio = abs(rewritten_len - orig_len) / max(1, orig_len)

        # 章を更新
        if self.repo and hasattr(self.repo, 'update_chapter_content'):
            res = self.repo.update_chapter_content(chapter.id, rewritten_text)
            if inspect.isawaitable(res):
                await res

        if reporter:
            reporter.report(f"Ep.{ep_num}: {dimension} 書き直し完了 ({orig_len}字 → {rewritten_len}字)", "info")

        return {
            "status": "success",
            "original_length": orig_len,
            "rewritten_length": rewritten_len,
            "diff_ratio": round(diff_ratio, 4),
            "execution_time_ms": exec_time_ms,
            "dimension": dimension,
            "instructions_applied": rewrite_instructions,
            "rewritten_text": rewritten_text,
        }