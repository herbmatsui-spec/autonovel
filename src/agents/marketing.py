# agents/marketing.py
import io
import json
import logging
import zipfile
from typing import Any

from src.agents.base import BaseAgent
from src.models.marketing_ctr import (
    TitleCandidate,
    ViralTitleRequest,
    ViralTitleResponse,
)
from src.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class MarketingAgent(BaseAgent):
    """マーケティング素材（表紙案、キャッチコピー、あらすじ）を生成するエージェント。"""

    def __init__(self, repo: Any = None, llm: LLMService | None = None, prompt_manager: Any = None):
        super().__init__(repo=repo, llm=llm)
        if prompt_manager is None:
            try:
                from prompts.manager import PromptManager

                prompt_manager = PromptManager()
            except Exception as e:
                logger.warning("PromptManager auto-init failed: %s", e)
                prompt_manager = None
        self.prompt_manager = prompt_manager

    async def generate_pack(
        self, book_title: str, synopsis: str, latest_ep: int, **kwargs
    ) -> dict[str, Any]:
        if self.prompt_manager is None:
            logger.warning("PromptManager unavailable — returning empty metadata fallback")
            return {"title": book_title, "tags": [], "synopsis": synopsis, "latest_ep": latest_ep}
        prompt = self.prompt_manager.build_marketing_pack_prompt(
            book_title=book_title, synopsis=synopsis, latest_ep=latest_ep, **kwargs
        )
        result = await self.llm.generate_json(purpose="marketing", prompt=prompt)
        if not isinstance(result, dict):
            return {"title": book_title, "tags": [], "synopsis": synopsis, "latest_ep": latest_ep}
        metadata = result.get("metadata")
        if not isinstance(metadata, dict) or not metadata:
            return {
                "title": result.get("title", book_title),
                "tags": result.get("tags", []) or [],
                "synopsis": result.get("synopsis", synopsis),
                "raw": result,
            }
        return metadata

    async def generate_viral_title_pack(
        self, request: ViralTitleRequest
    ) -> ViralTitleResponse:
        """カクヨムCTR最大化タイトル候補30〜50案を生成・採点し、上位推薦案とあらすじを返す。"""
        if self.prompt_manager is None:
            raise RuntimeError("PromptManager is unavailable")

        prompt = await self.prompt_manager.build_viral_title_prompt(
            genre=request.genre,
            core_concept=request.core_concept,
            protagonist_benefit=request.protagonist_benefit,
            antagonist_misfortune=request.antagonist_misfortune,
            candidate_count=request.candidate_count,
        )

        raw_candidates = await self.llm.generate_json(purpose="marketing", prompt=prompt)
        candidates_list = []
        if isinstance(raw_candidates, list):
            candidates_list = raw_candidates
        elif isinstance(raw_candidates, dict):
            candidates_list = (
                raw_candidates.get("candidates")
                or raw_candidates.get("titles")
                or [raw_candidates]
            )

        from src.services.marketing.ctr_scorer import score_title_ctr

        scored_candidates: list[TitleCandidate] = []
        for item in candidates_list:
            if isinstance(item, dict) and "title" in item:
                t_str = str(item["title"])
                syntax_type = str(item.get("syntax_type", "一般"))
                score_info = score_title_ctr(t_str)
                scored_candidates.append(
                    TitleCandidate(
                        title=t_str,
                        char_count=score_info["char_count"],
                        syntax_type=syntax_type,
                        predicted_ctr_score=score_info["score"],
                        hooks=score_info["hooks"],
                    )
                )

        # スコア降順ソート
        scored_candidates.sort(key=lambda c: c.predicted_ctr_score, reverse=True)

        if not scored_candidates:
            fallback_title = f"{request.core_concept}〜実は{request.protagonist_benefit}でした〜"
            scored_candidates.append(
                TitleCandidate(
                    title=fallback_title,
                    char_count=len(fallback_title),
                    syntax_type="一般",
                    predicted_ctr_score=75.0,
                    hooks=["実は"],
                )
            )

        top_recs = scored_candidates[:min(5, len(scored_candidates))]

        # 最上位タイトルに基づきあらすじを生成
        best_title = top_recs[0].title
        synopsis_prompt = await self.prompt_manager.build_viral_synopsis_prompt(
            selected_title=best_title,
            genre=request.genre,
            core_concept=request.core_concept,
            protagonist_benefit=request.protagonist_benefit,
            antagonist_misfortune=request.antagonist_misfortune,
        )
        synopsis_res = await self.llm.generate_text(purpose="marketing", prompt=synopsis_prompt)
        synopsis_text = str(synopsis_res).strip()

        return ViralTitleResponse(
            top_recommendations=top_recs,
            all_candidates=scored_candidates,
            selected_synopsis=synopsis_text,
        )

    async def run(self, *args, **kwargs):
        logger.info("MarketingAgent run invoked")
        return await self.generate_pack(**kwargs)

    @staticmethod
    async def _maybe_await(value: Any) -> Any:
        """coroutine なら await、それ以外はそのまま返すユーティリティ。"""
        if hasattr(value, "__await__"):
            return await value
        return value

    async def create_export_package(self, book_id: int, book_data: dict[str, Any] | None = None) -> tuple[bytes, str]:
        """作品データ一式（本文、設定、プロット、JSONダンプ）をZIPパッケージ化する。

        book_data が指定された場合、クライアントの最新ステート（本文・設定）を
        優先して反映する (かんたんモードの即時エクスポート用)。
        """
        # repo.get_book は同期/非同期の両実装に対応
        if self.repo is None:
            book = None
        else:
            get_book = getattr(self.repo, "get_book", None)
            if get_book is None:
                book = None
            else:
                result = get_book(book_id)
                # coroutine の場合は await する
                if hasattr(result, "__await__"):
                    book = await result
                else:
                    book = result
        if not book and not book_data:
            raise ValueError("作品が見つかりません。")

        branch_id = book.current_branch_id if book and book.current_branch_id else 1
        # book_data 提供時はクライアントの最新ステートを優先して反映
        override_title = book_data.get("title") if book_data else None
        override_genre = book_data.get("genre") if book_data else None
        override_chapters = book_data.get("chapters") if book_data else None
        override_characters = book_data.get("characters") if book_data else None
        override_plots = book_data.get("plots") if book_data else None

        # book_data 提供時は repo アクセスを省略 (同期/非同期の両実装に対応)
        chapters = []
        chars = []
        bible = None
        plots = []
        if book_data is None and self.repo is not None:
            chapters = await self._maybe_await(self.repo.get_all_non_anchor_chapters(
                book_id, branch_id=branch_id, order_by="ep_num"
            ))
            chars = await self._maybe_await(self.repo.get_all_characters(book_id))
            bible = await self._maybe_await(self.repo.get_latest_bible(book_id))
            plots = await self._maybe_await(self.repo.get_all_plots(book_id, branch_id=branch_id))

        # book_data 提供時は repo アクセスを省略しオーバーライド値を使用
        if book_data is not None:
            chapters = override_chapters if override_chapters is not None else chapters
            chars = override_characters if override_characters is not None else chars
            plots = override_plots if override_plots is not None else plots

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            # 01: 本文
            if book_data is not None and override_chapters is not None:
                full_text = "".join(
                    f"第{c.get('ep_num', i + 1)}話 {c.get('title', '')}\n\n{c.get('content', '')}\n\n"
                    for i, c in enumerate(override_chapters)
                )
            else:
                full_text = "".join(f"第{c.ep_num}話 {c.title}\n\n{c.content}\n\n" for c in chapters)
            z.writestr("01_本文.txt", full_text)

            # 02: キャラクター・世界観設定
            settings_str = ""
            if bible and bible.settings:
                settings_str = (
                    json.dumps(bible.settings, ensure_ascii=False, indent=2)
                    if isinstance(bible.settings, dict)
                    else str(bible.settings)
                )

            setting_text = f"【世界観設定】\n{settings_str}\n\n"
            setting_text += "【キャラクター設定】\n"
            if book_data is not None and override_characters is not None:
                # book_data のキャラクター設定 (dict 形式) を直接反映
                for c in override_characters:
                    if isinstance(c, dict):
                        setting_text += (
                            f"■ {c.get('name', '')} ({c.get('role', '')})\n"
                            f"性格: {c.get('personality', '')}\n"
                            f"能力: {c.get('ability', '')}\n\n"
                        )
                    else:
                        setting_text += f"■ {getattr(c, 'name', '')} ({getattr(c, 'role', '')})\n\n"
            else:
                for c in chars:
                    try:
                        if hasattr(c, "registry_data"):
                            reg = c.registry_data or {}
                            if isinstance(reg, str):
                                try:
                                    reg = json.loads(reg)
                                except (json.JSONDecodeError, ValueError):
                                    reg = {}
                        elif hasattr(c, "model_dump"):
                            reg = c.model_dump()
                        else:
                            reg = {}
                    except Exception:
                        reg = {}
                    setting_text += f"■ {c.name} ({c.role})\n性格: {reg.get('personality', '')}\n能力: {reg.get('ability', '')}\n\n"
            z.writestr("02_キャラクター・世界観設定集.txt", setting_text)

            # 03: プロット概要
            plot_text = "【プロット概要】\n"
            if book_data is not None and override_plots is not None:
                for p in override_plots:
                    if isinstance(p, dict):
                        plot_text += f"第{p.get('ep_num', '')}話: {p.get('title', '')}\n{p.get('one_line_summary', '')}\n\n"
                    else:
                        plot_text += f"第{getattr(p, 'ep_num', '')}話: {getattr(p, 'title', '')}\n\n"
            else:
                for p in plots:
                    plot_text += f"第{p.ep_num}話: {p.title}\n{p.one_line_summary or ''}\n\n"
            z.writestr("03_プロット概要.txt", plot_text)

            # 04: JSON ダンプ（機械可読）
            dump = {
                "book_id": book.id if book else book_id,
                "title": override_title if override_title else (book.title if book else ""),
                "genre": override_genre if override_genre else (book.genre if book else ""),
                "chapters": [
                    {"ep_num": c.ep_num, "title": c.title, "content": c.content}
                    for c in chapters
                ]
                if not (book_data is not None and override_chapters is not None)
                else [
                    {"ep_num": c.get("ep_num"), "title": c.get("title"), "content": c.get("content")}
                    for c in override_chapters
                ],
                "characters": [{"name": c.name, "role": c.role} for c in chars]
                if not (book_data is not None and override_characters is not None)
                else [
                    {"name": c.get("name"), "role": c.get("role"), "personality": c.get("personality")}
                    if isinstance(c, dict)
                    else {"name": getattr(c, "name", ""), "role": getattr(c, "role", "")}
                    for c in override_characters
                ],
                "plots": [
                    {"ep_num": p.ep_num, "title": p.title, "one_line_summary": p.one_line_summary}
                    for p in plots
                ]
                if not (book_data is not None and override_plots is not None)
                else [
                    {
                        "ep_num": p.get("ep_num"),
                        "title": p.get("title"),
                        "one_line_summary": p.get("one_line_summary"),
                    }
                    if isinstance(p, dict)
                    else {"ep_num": getattr(p, "ep_num", ""), "title": getattr(p, "title", "")}
                    for p in override_plots
                ],
            }
            z.writestr("04_データダンプ.json", json.dumps(dump, ensure_ascii=False, indent=2))

        zip_data = buf.getvalue()
        zip_filename = f"export_{book_id}.zip"
        return zip_data, zip_filename
