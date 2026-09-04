# src/agents/skills/marketing_copy.py
"""マーケティングコピー生成スキル（サンプル実装）"""
from typing import Any
from src.agents.skill_base import SkillAgent
from src.agents.orchestrator import AgentContext, AgentResult


class MarketingCopySkill(SkillAgent):
    """作品のプロモーション用コピーを生成するスキル"""

    def __init__(self, *args, copy_types: list[str] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.copy_types = copy_types or ["catchphrase", "synopsis", "tagline", "blurb"]

    async def execute(self, ctx: AgentContext) -> AgentResult:
        """マーケティングコピーを生成"""
        self.emit_event("marketing_copy.started", {
            "book_id": ctx.book_id,
            "title": ctx.artifacts.get("title", ""),
        })
        
        title = ctx.artifacts.get("title", "")
        synopsis = ctx.artifacts.get("synopsis", "")
        genre = ctx.artifacts.get("genre", "ファンタジー")
        concept = ctx.artifacts.get("concept", "")

        if not title:
            self.emit_event("marketing_copy.error", {
                "book_id": ctx.book_id,
                "error": "title is required for marketing copy generation",
            })
            return AgentResult(
                next_agent=None,
                artifacts={},
                error="title is required for marketing copy generation",
            )

        copies = {}

        # キャッチフレーズ
        if "catchphrase" in self.copy_types:
            copies["catchphrase"] = self._generate_catchphrase(title, genre, concept)

        # あらすじ（プロモ用短縮版）
        if "synopsis" in self.copy_types:
            copies["synopsis"] = self._generate_promo_synopsis(synopsis, genre)

        # タグライン
        if "tagline" in self.copy_types:
            copies["tagline"] = self._generate_tagline(title, genre)

        # ブラーブ（裏表紙用紹介文）
        if "blurb" in self.copy_types:
            copies["blurb"] = self._generate_blurb(title, synopsis, genre)

        self.emit_event("marketing_copy.completed", {
            "book_id": ctx.book_id,
            "copies_generated": list(copies.keys()),
        })
        
        return AgentResult(
            next_agent=None,
            artifacts={"marketing_copies": copies},
        )

    def _generate_catchphrase(self, title: str, genre: str, concept: str) -> str:
        """キャッチフレーズ生成（簡易テンプレート）"""
        templates = {
            "ファンタジー": f"運命を切り拓く、{title}の物語",
            "SF": f"未来を変える鍵は、{title}にある",
            "恋愛": f"恋が世界を変える、{title}",
            "ミステリ": f"真実はいつも、{title}の中に",
            "ホラー": f"恐怖の扉が開く、{title}",
        }
        return templates.get(genre, f"新たな伝説の始まり、{title}")

    def _generate_promo_synopsis(self, synopsis: str, genre: str) -> str:
        """プロモ用あらすじ生成"""
        if len(synopsis) > 200:
            return synopsis[:200] + "……"
        return synopsis

    def _generate_tagline(self, title: str, genre: str) -> str:
        """タグライン生成"""
        return f"{title} ― あなたの知らない物語"

    def _generate_blurb(self, title: str, synopsis: str, genre: str) -> str:
        """ブラーブ生成"""
        return f"『{title}』\n\n{synopsis[:300]}\n\n――これは、{genre}の新たな地平を切り拓く一作。"