# src/agents/context_builder_agent.py
from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel

from src.agents.skill_base import SkillAgent
from src.agents.orchestrator import AgentContext, AgentResult, AgentName
from src.services.compression.models import ProtectedContext


class ContextBuilderInput(BaseModel):
    plot: dict[str, Any]
    target_word_count: int
    style_tag: str | None = None


class ContextBuilderOutput(BaseModel):
    full_context: dict[str, Any]


class ContextBuilderAgent(SkillAgent):
    """執筆に必要な完全なコンテキストを構築するエージェント。"""

    def __init__(
        self,
        repo: Any = None,
        llm: Any = None,
        style_rag: Any = None,
        rag_prefetch: Any = None,
        event_bus: Any = None,
        reflective_rag: Any = None,
        compressor: Any = None,
        social_manager: Any = None,
        age_client: Any = None,
    ):
        super().__init__(
            repo=repo,
            llm=llm,
            style_rag=style_rag,
            rag_prefetch=rag_prefetch,
            event_bus=event_bus,
        )
        self.reflective_rag = reflective_rag
        self.compressor = compressor
        self.social_manager = social_manager
        self.age_client = age_client

    async def execute(self, ctx: AgentContext) -> AgentResult:
        """スキル実行エントリーポイント。"""
        self.emit_event("context_builder.started", {
            "book_id": ctx.book_id,
            "ep_num": ctx.ep_num,
        })
        
        repo = ctx.artifacts.get("repo")
        if repo is None:
            self.emit_event("context_builder.error", {
                "book_id": ctx.book_id,
                "ep_num": ctx.ep_num,
                "error": "repo is required in artifacts",
            })
            return AgentResult(
                next_agent=None,
                artifacts={},
                error="repo is required in artifacts",
            )

        book_id = ctx.book_id
        branch_id = ctx.branch_id
        ep_num = ctx.ep_num
        target_word_count = ctx.artifacts.get("target_word_count", 3000)
        style_tag = ctx.artifacts.get("style_tag")
        regeneration_focus = ctx.artifacts.get("regeneration_focus")  # 再生成フォーカス

        reflective_rag = ctx.artifacts.get("reflective_rag") or self.reflective_rag
        session = ctx.artifacts.get("session") or getattr(repo, "session", None)
        compressor = ctx.artifacts.get("compressor") or self.compressor
        social_manager = ctx.artifacts.get("social_manager") or self.social_manager
        age_client = ctx.artifacts.get("age_client") or self.age_client

        # 既存の内部実装ロジックを流用
        full_context = await self._build_full_writing_context_internal(
            repo,
            book_id,
            branch_id,
            ep_num,
            target_word_count,
            style_tag,
            regeneration_focus,
            reflective_rag=reflective_rag,
            session=session,
            compressor=compressor,
            social_manager=social_manager,
            age_client=age_client,
        )

        self.emit_event("context_builder.completed", {
            "book_id": book_id,
            "ep_num": ep_num,
        })
        
        res_artifacts = dict(ctx.artifacts)
        res_artifacts["writing_context"] = full_context
        return AgentResult(
            next_agent=AgentName.WRITING,
            artifacts=res_artifacts,
        )

    def allocate_token_budgets(self, total_budget: int = 4000, scene_type: str = "general") -> dict[str, int]:
        """Automatically arbitrate token budgets between RAG and compression based on scene type (Step 63)."""
        st = str(scene_type).lower()
        if st in ("mystery", "political", "flashback"):
            rag_ratio = 0.55
        elif st in ("romance", "daily"):
            rag_ratio = 0.25
        elif st in ("combat", "survival"):
            rag_ratio = 0.30
        else:
            rag_ratio = 0.40

        rag_budget = int(total_budget * rag_ratio)
        comp_budget = total_budget - rag_budget
        return {
            "rag_budget": rag_budget,
            "compression_budget": comp_budget,
        }

    async def run(self, ctx: AgentContext) -> AgentResult:
        """Orchestrator 用エントリーポイント。execute をラップする。"""
        return await self.execute(ctx)

    async def _build_full_writing_context_internal(
        self,
        repo: Any,
        book_id: int,
        branch_id: int,
        ep_num: int,
        target_word_count: int,
        style_tag: str | None = None,
        regeneration_focus: list[str] | None = None,
        reflective_rag: Any = None,
        session: Any = None,
        compressor: Any = None,
        social_manager: Any = None,
        age_client: Any = None,
    ) -> dict[str, Any]:
        """内部実装: 執筆に必要な完全なコンテキストを構築する。"""
        plot = await self._get_plot(repo, book_id, branch_id, ep_num)
        if plot is None:
            plot = await self._ensure_plot_exists(repo, book_id, branch_id, ep_num)

        _ = await self._get_book(repo, book_id)
        chars = await self._get_chars(repo, book_id)
        prev_chapter = await self._get_prev_chapter(repo, book_id, branch_id, ep_num)

        active_chars = await self._get_active_chars(chars, plot)
        
        # Step 53: ソーシャル関係性・直近ジャーナルの動的コンテキスト取得
        social_ctx = await self._get_social_dynamic_context(
            session=session,
            age_client=age_client,
            social_manager=social_manager,
            book_id=book_id,
            ep_num=ep_num,
            active_chars=active_chars,
        )

        # 再生成フォーカスに応じてキャラクター情報を強化
        if regeneration_focus and "coherency" in regeneration_focus:
            # 口調・世界観ルールをより詳細に含める
            char_static_ctx = self._build_char_static_ctx(active_chars, detailed=True)
            char_dynamic_ctx = self._build_char_dynamic_ctx(
                active_chars, prev_chapter, include_status_history=True, social_context=social_ctx
            )
        else:
            char_static_ctx = self._build_char_static_ctx(active_chars)
            char_dynamic_ctx = self._build_char_dynamic_ctx(
                active_chars, prev_chapter, social_context=social_ctx
            )
        
        # 再生成フォーカスに応じて前話文脈を強化
        if regeneration_focus and "structure" in regeneration_focus:
            prev_ctx = self._build_prev_ctx(prev_chapter, book_id, branch_id, ep_num, include_arc_info=True)
        else:
            prev_ctx = self._build_prev_ctx(prev_chapter, book_id, branch_id, ep_num)
        
        dialogue_profiles = self._build_dialogue_profiles(active_chars)

        plot_dict = {}
        if plot is not None:
            if hasattr(plot, "model_dump") and callable(getattr(plot, "model_dump")):
                try:
                    dumped = plot.model_dump()
                    if isinstance(dumped, dict):
                        plot_dict = dumped
                except Exception:
                    pass
            if not plot_dict:
                if isinstance(plot, dict):
                    plot_dict = plot
                else:
                    plot_dict = {
                        "ep_num": ep_num,
                        "detailed_blueprint": getattr(plot, "detailed_blueprint", "") or "",
                        "scenes": getattr(plot, "scenes", []) or [],
                        "summary": getattr(plot, "summary", "") or "",
                        "current_chain_phase": getattr(plot, "current_chain_phase", "Friction")
                        or "Friction",
                        "title": getattr(plot, "title", "") or "",
                        "tension": getattr(plot, "tension", 50) or 50,
                    }
        else:
            plot_dict = {
                "ep_num": ep_num,
                "detailed_blueprint": "",
                "scenes": [],
                "summary": "",
                "current_chain_phase": "Friction",
            }

        pov_name = ""
        if active_chars:
            pov_name = getattr(active_chars[0], "name", "") or ""

        tension_val = plot_dict.get("tension", 50)
        try:
            tension_int = int(tension_val)
        except (ValueError, TypeError):
            tension_int = 50

        density_level = "Standard"
        if tension_int >= 80 or getattr(plot, "is_catharsis", False):
            density_level = "Extreme"
        elif tension_int >= 60:
            density_level = "High"

        # Step 21 & 62: 反射的検索 (Reflective RAG) の実行（シーン意図の注入）
        rag_context = []
        if reflective_rag is not None:
            query = (
                plot_dict.get("summary")
                or plot_dict.get("title")
                or f"episode {ep_num} context"
            )
            scene_intent = plot_dict.get("summary", "")
            try:
                import inspect
                res = reflective_rag.retrieve_with_reflection(
                    session=session,
                    query=query,
                    scene_intent=scene_intent,
                    book_id=book_id,
                )
                if inspect.iscoroutine(res):
                    res = await res
                if res and hasattr(res, "documents"):
                    for doc in res.documents:
                        rag_context.append({
                            "content": getattr(doc, "content", str(doc)),
                            "metadata": getattr(doc, "metadata", {}),
                            "score": getattr(doc, "score", getattr(doc, "similarity", 0.0)),
                        })
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Reflective RAG retrieval failed: {e}")

        # Step 33 & 61: 4階層コンテキスト圧縮 (FourLayerCompressor) の統合（ProtectedContext注入）
        compressed_context = ""
        compression_stats: dict[str, Any] = {}
        if compressor is not None:
            raw_corpus = f"{prev_ctx}\n{char_static_ctx}\n{plot_dict.get('summary', '')}"
            s_type = "general"
            scene_weights = None
            
            # Try to get multi-label detection from compressor or its layer4
            detector = None
            if hasattr(compressor, "detect_scene_type_multi") and callable(compressor.detect_scene_type_multi):
                detector = compressor.detect_scene_type_multi
            elif hasattr(getattr(compressor, "layer4", None), "detect_scene_type_multi"):
                detector = compressor.layer4.detect_scene_type_multi
            elif hasattr(compressor, "detect_scene_type") and callable(compressor.detect_scene_type):
                detector = compressor.detect_scene_type
            elif hasattr(getattr(compressor, "layer4", None), "detect_scene_type"):
                detector = compressor.layer4.detect_scene_type
            
            if detector:
                multi = detector(plot_dict.get("summary", ""), plot_dict.get("scenes", []))
                if multi:
                    if isinstance(multi, list) and multi and isinstance(multi[0], tuple):
                        s_type = multi[0][0]
                        scene_weights = {st: conf for st, conf in multi}
                    else:
                        s_type = multi

            # Build ProtectedContext for guaranteed retention of active characters & foreshadowings (Step 61)
            active_char_names = [getattr(c, "name", str(c)) for c in (active_chars or []) if c]
            foreshadowing_ids = [
                str(fs.get("id")) for fs in plot_dict.get("foreshadowings", [])
                if isinstance(fs, dict) and fs.get("id")
            ]
            protected_ctx = ProtectedContext(
                active_characters=active_char_names,
                pending_foreshadowing_ids=foreshadowing_ids,
            )

            try:
                import inspect
                c_res = compressor.compress(
                    raw_corpus,
                    session=session,
                    book_id=book_id,
                    ep_num=ep_num,
                    scene_type=s_type,
                    scene_weights=scene_weights,
                    protected_context=protected_ctx,
                )
                if inspect.iscoroutine(c_res):
                    c_res = await c_res
                if c_res and hasattr(c_res, "final_context_text"):
                    compressed_context = c_res.final_context_text
                    compression_stats = {
                        "reduction_ratio": getattr(c_res, "overall_reduction_ratio", 0.0),
                        "final_tokens": getattr(c_res, "final_token_count", 0),
                        "from_cache": getattr(c_res, "from_cache", False),
                        "scene_type": getattr(c_res, "layer4", None).scene_type if getattr(c_res, "layer4", None) else s_type,
                        "scene_weights": scene_weights,
                    }
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Context compression failed: {e}")

        return {
            "plot": plot_dict,
            "target_word_count": target_word_count,
            "style_tag": style_tag,
            "char_static_ctx": char_static_ctx,
            "char_dynamic_ctx": char_dynamic_ctx,
            "prev_ctx": prev_ctx,
            "pov_character_name": pov_name,
            "dialogue_profiles": dialogue_profiles,
            "density_level": density_level,
            "rag_context": rag_context,
            "compressed_context": compressed_context,
            "compression_stats": compression_stats,
        }

    # デリゲートメソッド群（repo を直接受け取るように変更）
    async def _get_plot(self, repo: Any, book_id: int, branch_id: int, ep_num: int) -> Any | None:
        """プロットをDBから取得する。"""
        if repo is None:
            return None
        try:
            return await repo.get_plot(book_id, ep_num, branch_id=branch_id)
        except Exception as e:
            if hasattr(self, "logger"):
                self.logger.debug(
                    f"Plot not found for book={book_id}, branch={branch_id}, ep={ep_num}: {e}"
                )
            return None

    async def _get_book(self, repo: Any, book_id: int) -> Any | None:
        """作品情報をDBから取得する。"""
        if repo is None:
            return None
        try:
            return await repo.get_book(book_id)
        except Exception as e:
            if hasattr(self, "logger"):
                self.logger.debug(f"Book not found for book_id={book_id}: {e}")
            return None

    async def _get_chars(self, repo: Any, book_id: int) -> list[Any]:
        """作品に所属する全キャラクターを取得する。"""
        if repo is None:
            return []
        try:
            return await repo.get_all_characters(book_id)
        except Exception as e:
            if hasattr(self, "logger"):
                self.logger.debug(f"Characters not found for book_id={book_id}: {e}")
            return []

    async def _get_prev_chapter(
        self, repo: Any, book_id: int, branch_id: int, ep_num: int
    ) -> Any | None:
        """前話の章データを取得する。"""
        if repo is None or ep_num <= 1:
            return None
        try:
            return await repo.get_chapter(branch_id, ep_num - 1)
        except Exception as e:
            if hasattr(self, "logger"):
                self.logger.debug(
                    f"Previous chapter not found for book={book_id}, branch={branch_id}, ep={ep_num}: {e}"
                )
            return None

    async def _get_active_chars(self, chars: list[Any], plot: Any) -> list[Any]:
        """プロットに登場するキャラクター名からアクティブなキャラクターを抽出する。"""
        if not plot or not chars:
            return chars
        try:
            plot_text = ""
            if hasattr(plot, "detailed_blueprint") and plot.detailed_blueprint:
                plot_text = plot.detailed_blueprint
            elif hasattr(plot, "summary") and plot.summary:
                plot_text = plot.summary
            if not plot_text:
                return chars
            active_names = set()
            for char in chars:
                name = getattr(char, "name", None)
                if name and name in plot_text:
                    active_names.add(name)
            if active_names:
                return [c for c in chars if getattr(c, "name", None) in active_names]
            return chars
        except Exception as e:
            if hasattr(self, "logger"):
                self.logger.debug(f"Active char extraction failed: {e}")
            return chars

    def _build_char_static_ctx(self, chars: list[Any], detailed: bool = False) -> str:
        """キャラクターの不変属性を整形する。"""
        if not chars:
            return ""
        lines = []
        for char in chars:
            name = getattr(char, "name", "不明")
            role = getattr(char, "role", "")
            reg = char.to_safe_dict() if hasattr(char, "to_safe_dict") else {}
            surface = reg.get("surface_persona", "")
            personality = reg.get("personality", reg.get("inner_conflict", ""))
            parts = [f"- {name} ({role})"]
            if surface:
                parts.append(f"  表層: {surface}")
            if personality:
                parts.append(f"  内面: {personality}")
            if detailed:
                # 詳細モード: 口調サンプル・語彙傾向も含める
                speech_sample = reg.get("speech_sample", reg.get("口調サンプル", ""))
                vocab_tendency = reg.get("vocab_tendency", reg.get("語彙傾向", ""))
                if speech_sample:
                    parts.append(f"  口調サンプル: {speech_sample}")
                if vocab_tendency:
                    parts.append(f"  語彙傾向: {vocab_tendency}")
            lines.append("\n".join(parts))
        return "\n".join(lines)

    def _build_char_dynamic_ctx(
        self,
        chars: list[Any],
        prev_chapter: Any | None,
        include_status_history: bool = False,
        social_context: str | None = None,
    ) -> str:
        """キャラクターの動的状態を整形する。"""
        if not chars:
            return ""
        lines = []
        for char in chars:
            name = getattr(char, "name", "不明")
            reg = char.to_safe_dict() if hasattr(char, "to_safe_dict") else {}
            location = reg.get("location", "不明")
            inventory = reg.get("inventory", [])
            status = reg.get("status", "通常")
            parts = [f"- {name}: 場所={location}, 状態={status}"]
            if inventory:
                parts.append(f"  所持: {', '.join(inventory)}")
            lines.append("\n".join(parts))
        ctx = "\n".join(lines)
        if prev_chapter:
            ws = getattr(prev_chapter, "world_state", None)
            if ws:
                if isinstance(ws, str):
                    try:
                        ws = json.loads(ws)
                    except Exception:
                        ws = None
                if isinstance(ws, dict):
                    changes = ws.get("character_status_changes", [])
                    if changes:
                        ctx += "\n\n【前話でのステータス変更】\n"
                        ctx += "\n".join([f"- {c}" for c in changes[:10]])

        # Step 53: ソーシャルジャーナル・関係性推移の文脈追加
        if social_context and social_context.strip():
            ctx += f"\n\n{social_context.strip()}"

        return ctx

    async def _get_social_dynamic_context(
        self,
        session: Any = None,
        age_client: Any = None,
        social_manager: Any = None,
        book_id: int = 1,
        ep_num: int = 1,
        active_chars: list[Any] | None = None,
        max_chars: int = 1200,
    ) -> str:
        """Step 53 & Steps 30-36: 直近エピソードのソーシャルジャーナルと動的関係性トレンドを取得・整形する（耐障害・文字数制限付き）。"""
        import logging
        logger = logging.getLogger(__name__)

        try:
            parts = []
            char_names = set()
            if active_chars:
                for c in active_chars:
                    name = getattr(c, "name", None) or (c.get("name") if isinstance(c, dict) else None)
                    if name:
                        char_names.add(str(name).strip())

            social_repo = getattr(social_manager, "social_repo", None)

            # 1. SocialRepository からの重要手記・動的関係性トレンド取得 (Step 30, 31, 33)
            if social_repo is not None:
                try:
                    j_sum = await social_repo.get_important_journals_summary(
                        book_id=book_id, current_ep=ep_num, lookback=5
                    )
                    if j_sum:
                        parts.append(j_sum)

                    # アクティブキャラクターが指定されている場合は関連ペアを優先抽出
                    if char_names:
                        active_rels = await social_repo.get_relationships_for_characters(
                            book_id=book_id, char_names=list(char_names)
                        )
                        if active_rels:
                            rel_lines = []
                            for r in active_rels[:6]:
                                rel_lines.append(
                                    f"- {r['char_a']} ⇔ {r['char_b']} [{r['dynamics_state']}]: "
                                    f"信頼度={r['trust']:.0f}, 緊張度={r['tension']:.0f}, 好感度={r['affection']:.0f}"
                                )
                            parts.append("【登場キャラクター間の動的関係性 (Social Dynamics)】\n" + "\n".join(rel_lines))
                    else:
                        t_sum = await social_repo.get_relationship_trends_summary(book_id=book_id)
                        if t_sum:
                            parts.append(t_sum)

                except Exception as e:
                    logger.debug("Failed to retrieve social summaries from repository: %s", e)

            # 2. フォールバック: AGE からの直前話ジャーナル取得試行 (未取得時)
            if not any("内面手記" in p for p in parts) and age_client and session and ep_num > 1:
                try:
                    prev_ep = ep_num - 1
                    cypher = (
                        f"MATCH (j:journal_entry) "
                        f"WHERE j.book_id = {book_id} AND j.ep_num = {prev_ep} "
                        f"RETURN j.character_name as name, j.emotion as emotion, j.theme as theme, j.content as content "
                        f"LIMIT 5"
                    )
                    res = age_client.execute_cypher(session, cypher)
                    if res and getattr(res, "records", None):
                        j_lines = []
                        for r in res.records:
                            c_name = r.get("name", "登場人物")
                            emo = r.get("emotion", "")
                            cnt = r.get("content", "")
                            j_lines.append(f"- {c_name}（感情: {emo}）: 「{cnt[:120]}」")
                        if j_lines:
                            parts.append("【直前話の登場人物内面手記・独白 (Apache AGE)】\n" + "\n".join(j_lines))
                except Exception as e:
                    logger.debug("Failed to retrieve journals from AGE: %s", e)

            # 3. フォールバック: SocialInteractionManager からの関係性メトリクス取得 (未取得時)
            if not any("動的関係性" in p or "動的心理関係性" in p for p in parts) and social_manager:
                try:
                    rel_lines = []
                    seen_pairs = set()
                    names_to_check = list(char_names) or ["主人公", "ライバル"]
                    for name in names_to_check:
                        rels = social_manager.get_all_relationships_for_character(name)
                        for r in rels:
                            pair = tuple(sorted([r.char_a, r.char_b]))
                            if pair in seen_pairs:
                                continue
                            seen_pairs.add(pair)
                            rel_lines.append(
                                f"- {r.char_a} ⇔ {r.char_b}: 信頼度={r.trust_score}, 緊張度={r.tension_score}, 好感度={r.affinity_score}"
                            )
                    if rel_lines:
                        parts.append("【登場人物間の動的心理関係性 (Social Dynamics)】\n" + "\n".join(rel_lines[:6]))
                except Exception as e:
                    logger.debug("Failed to retrieve relationships from social_manager: %s", e)

            result_text = "\n\n".join(parts)
            # Step 34: トークン予算（文字数上限）による安全トリミング
            if len(result_text) > max_chars:
                result_text = result_text[:max_chars - 3] + "..."

            return result_text

        except Exception as e:
            # Step 36: 予期せぬ障害時でも小説生成フローを絶対に止めない
            logger.warning("Unexpected error in _get_social_dynamic_context, falling back gracefully: %s", e)
            return ""

    def _build_prev_ctx(
        self, prev_chapter: Any | None, book_id: int, branch_id: int, ep_num: int, include_arc_info: bool = False
    ) -> str:
        """前話までの文脈を整形する。"""
        if prev_chapter is None:
            return ""
        parts = []
        content = getattr(prev_chapter, "content", None)
        if content:
            parts.append(f"【前話本文(末尾500文字)】\n{content[-500:]}")
        summary = getattr(prev_chapter, "summary", None)
        if summary:
            parts.append(f"【前話あらすじ】\n{summary}")
        ai_insight = getattr(prev_chapter, "ai_insight", None)
        if ai_insight:
            parts.append(f"【前話の確定事実・伏線回収】\n{ai_insight}")
        if include_arc_info:
            # アーク情報を追加（構造フォーカス時）
            arc_info = getattr(prev_chapter, "arc_info", None)
            if arc_info:
                parts.append(f"【アーク情報】\n{arc_info}")
        if not parts:
            return ""
        return "\n\n".join(parts)

    def _build_dialogue_profiles(self, chars: list[Any]) -> dict[str, str]:
        """各キャラクターの会話プロファイルを構築する。"""
        profiles = {}
        for char in chars:
            name = getattr(char, "name", None)
            if not name:
                continue
            reg = char.to_safe_dict() if hasattr(char, "to_safe_dict") else {}
            parts = []
            if reg.get("speech_pattern"):
                parts.append(f"話し方: {reg['speech_pattern']}")
            if reg.get("forbidden_words"):
                parts.append(f"禁止語: {', '.join(reg['forbidden_words'])}")
            if reg.get("catchphrase"):
                parts.append(f"口癖: {reg['catchphrase']}")
            profiles[name] = "; ".join(parts) if parts else name
        return profiles

    async def _ensure_plot_exists(
        self, repo: Any, book_id: int, branch_id: int, ep_num: int
    ) -> Any | None:
        """プロットが存在しない場合、生成を試みる。"""
        plot = await self._get_plot(repo, book_id, branch_id, ep_num)
        if (
            plot is None
            and hasattr(self, "_plot_expander")
            and getattr(self, "_plot_expander") is not None
        ):
            try:
                if hasattr(self, "logger"):
                    self.logger.info(
                        f"Plot missing for Ep.{ep_num}, attempting on-demand generation..."
                    )
                arcs: list[Any] = []
                bible = await self._get_bible(repo, book_id)
                if bible and hasattr(bible, "arcs"):
                    arcs = bible.arcs
                elif bible and isinstance(bible, dict):
                    arcs = bible.get("arcs", [])
                results = await self._plot_expander.expand_plots(
                    book_id=book_id,
                    target_ep_list=[ep_num],
                    arcs=arcs,
                    reporter=None,
                    force=False,
                    branch_id=branch_id,
                )
                if results:
                    plot = results[0]
                    if hasattr(self, "logger"):
                        self.logger.info(f"On-demand plot generated for Ep.{ep_num}")
            except Exception as e:
                if hasattr(self, "logger"):
                    self.logger.warning(f"On-demand plot generation failed for Ep.{ep_num}: {e}")
        return plot

    async def _get_bible(self, repo: Any, book_id: int) -> Any | None:
        """最新のバイブルを取得する。"""
        if repo is None:
            return None
        try:
            return await repo.get_latest_bible(book_id)
        except Exception as e:
            if hasattr(self, "logger"):
                self.logger.debug(f"Bible not found for book_id={book_id}: {e}")
            return None
