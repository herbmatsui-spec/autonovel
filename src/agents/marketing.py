# agents/marketing.py
import io
import json
import logging
import zipfile
from typing import Any

from src.agents.base import BaseAgent
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

    async def run(self, *args, **kwargs):
        logger.info("MarketingAgent run invoked")
        return await self.generate_pack(**kwargs)

    async def create_export_package(self, book_id: int) -> tuple[bytes, str]:
        """作品データ一式（本文、設定、プロット、JSONダンプ）をZIPパッケージ化する"""
        book = await self.repo.get_book(book_id)
        if not book:
            raise ValueError("作品が見つかりません。")

        branch_id = book.current_branch_id if book and book.current_branch_id else 1

        chapters = await self.repo.get_all_non_anchor_chapters(
            book_id, branch_id=branch_id, order_by="ep_num"
        )
        chars = await self.repo.get_all_characters(book_id)
        bible = await self.repo.get_latest_bible(book_id)
        plots = await self.repo.get_all_plots(book_id, branch_id=branch_id)

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            # 01: 本文
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
            for p in plots:
                plot_text += f"第{p.ep_num}話: {p.title}\n{p.one_line_summary or ''}\n\n"
            z.writestr("03_プロット概要.txt", plot_text)

            # 04: JSON ダンプ（機械可読）
            dump = {
                "book_id": book.id,
                "title": book.title,
                "genre": book.genre,
                "chapters": [
                    {"ep_num": c.ep_num, "title": c.title, "content": c.content} for c in chapters
                ],
                "characters": [{"name": c.name, "role": c.role} for c in chars],
                "plots": [
                    {"ep_num": p.ep_num, "title": p.title, "one_line_summary": p.one_line_summary}
                    for p in plots
                ],
            }
            z.writestr("04_データダンプ.json", json.dumps(dump, ensure_ascii=False, indent=2))

        zip_data = buf.getvalue()
        zip_filename = f"export_{book_id}.zip"
        return zip_data, zip_filename
