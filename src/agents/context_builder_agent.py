# src/agents/context_builder_agent.py
from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel

from src.agents.base import BaseAgent
from src.agents.orchestrator import AgentContext, AgentResult, AgentName


class ContextBuilderInput(BaseModel):
    plot: dict[str, Any]
    target_word_count: int
    style_tag: str | None = None


class ContextBuilderOutput(BaseModel):
    full_context: dict[str, Any]


class ContextBuilderAgent(BaseAgent):
    """執筆に必要な完全なコンテキストを構築するエージェント。"""

    async def run(self, ctx: AgentContext) -> AgentResult:
        """Orchestrator 用エントリーポイント。
        ctx.artifacts から必要な依存データを取得し、コンテキストを構築する。
        """
        repo = ctx.artifacts.get("repo")
        if repo is None:
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

        # 既存の内部実装ロジックを流用
        full_context = await self._build_full_writing_context_internal(
            repo, book_id, branch_id, ep_num, target_word_count, style_tag
        )

        return AgentResult(
            next_agent=AgentName.WRITING,
            artifacts={"writing_context": full_context},
        )

    async def _build_full_writing_context_internal(
        self,
        repo: Any,
        book_id: int,
        branch_id: int,
        ep_num: int,
        target_word_count: int,
        style_tag: str | None = None,
    ) -> dict[str, Any]:
        """内部実装: 執筆に必要な完全なコンテキストを構築する。"""
        plot = await self._get_plot(repo, book_id, branch_id, ep_num)
        if plot is None:
            plot = await self._ensure_plot_exists(repo, book_id, branch_id, ep_num)

        book = await self._get_book(repo, book_id)
        chars = await self._get_chars(repo, book_id)
        prev_chapter = await self._get_prev_chapter(repo, book_id, branch_id, ep_num)

        active_chars = await self._get_active_chars(chars, plot)
        char_static_ctx = self._build_char_static_ctx(active_chars)
        char_dynamic_ctx = self._build_char_dynamic_ctx(active_chars, prev_chapter)
        prev_ctx = self._build_prev_ctx(prev_chapter, book_id, branch_id, ep_num)
        dialogue_profiles = self._build_dialogue_profiles(active_chars)

        plot_dict = {}
        if plot is not None:
            if hasattr(plot, "model_dump"):
                plot_dict = plot.model_dump()
            elif isinstance(plot, dict):
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

        density_level = "Standard"
        if plot_dict.get("tension", 50) >= 80 or getattr(plot, "is_catharsis", False):
            density_level = "Extreme"
        elif plot_dict.get("tension", 50) >= 60:
            density_level = "High"

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

    async def _get_prev_chapter(self, repo: Any, book_id: int, branch_id: int, ep_num: int) -> Any | None:
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

    def _build_char_static_ctx(self, chars: list[Any]) -> str:
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
            lines.append("\n".join(parts))
        return "\n".join(lines)

    def _build_char_dynamic_ctx(self, chars: list[Any], prev_chapter: Any | None) -> str:
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
        return ctx

    def _build_prev_ctx(
        self, prev_chapter: Any | None, book_id: int, branch_id: int, ep_num: int
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

    async def _ensure_plot_exists(self, repo: Any, book_id: int, branch_id: int, ep_num: int) -> Any | None:
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
                    self.logger.warning(
                        f"On-demand plot generation failed for Ep.{ep_num}: {e}"
                    )
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