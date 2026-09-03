# tests/mocks/__init__.py
"""テスト用モックヘルパー。"""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock


class MockLLMAdapter:
    """LLM アダプタのモック。"""

    def __init__(self, responses: dict[str, Any] | None = None):
        self.responses = responses or {}
        self.call_count = 0

    async def generate_json(self, purpose: str, prompt: str, response_schema: Any = None) -> dict[str, Any]:
        self.call_count += 1
        key = f"{purpose}:{self.call_count}"
        if key in self.responses:
            return self.responses[key]
        # デフォルト成功レスポンス
        return {
            "success": True,
            "metadata": self._default_metadata(purpose),
        }

    async def generate_text(self, prompt: str, system_prompt: str = "", max_tokens: int = 2000) -> str:
        self.call_count += 1
        return self.responses.get(f"text:{self.call_count}", "モック生成本文です。" * 50)

    def _default_metadata(self, purpose: str) -> dict[str, Any]:
        defaults = {
            "planning": {"arcs": [{"title": "第1章", "start_ep": 1, "end_ep": 3, "summary": "導入"}]},
            "plot": {"ep_num": 1, "title": "第1話", "detailed_blueprint": "プロット詳細", "summary": "あらすじ"},
            "bible": {"settings": {"world": "ファンタジー"}, "characters": []},
            "audit": {"is_valid": True, "feedback": "OK"},
            "marketing": {"title": "テスト作品", "tags": ["ファンタジー"], "synopsis": "あらすじ"},
        }
        return defaults.get(purpose, {})


class MockPromptManager:
    """PromptManager のモック。"""

    def build_arc_generation_prompt(self, **kwargs) -> str:
        return "arc prompt"

    def build_world_creation_prompt(self, **kwargs) -> str:
        return "world prompt"

    def build_expansion_prompt(self, **kwargs) -> str:
        return "expansion prompt"

    def build_marketing_pack_prompt(self, **kwargs) -> str:
        return "marketing prompt"


class MockBookRepository:
    """BookRepository のモック。"""

    def __init__(self):
        self.books = {
            1: MagicMock(
                id=1,
                title="テスト作品",
                genre="ファンタジー",
                current_branch_id=1,
            )
        }
        self.chapters = {}
        self.plots = {}
        self.characters = []
        self.bibles = {}
        self.tasks = {}

    async def get_book(self, book_id: int):
        return self.books.get(book_id)

    async def get_chapter(self, branch_id: int, ep_num: int):
        return self.chapters.get((branch_id, ep_num))

    async def get_plot(self, book_id: int, ep_num: int, branch_id: int = 1):
        return self.plots.get((book_id, branch_id, ep_num))

    async def get_all_characters(self, book_id: int):
        return self.characters

    async def get_latest_bible(self, book_id: int):
        return self.bibles.get(book_id)

    async def get_all_non_anchor_chapters(self, book_id: int, branch_id: int = 1, order_by: str = "ep_num"):
        return [c for (b, e), c in self.chapters.items() if b == branch_id]

    async def get_all_plots(self, book_id: int, branch_id: int = 1):
        return [p for (bk, b, e), p in self.plots.items() if bk == book_id and b == branch_id]

    async def create_task(self, task_id: str, status: str):
        self.tasks[task_id] = {"status": status}

    async def update_task_status(self, task_id: str, status: str):
        if task_id in self.tasks:
            self.tasks[task_id]["status"] = status

    async def set_task_result(self, task_id: str, result_json: str):
        if task_id in self.tasks:
            self.tasks[task_id]["result"] = result_json


class MockImageService:
    """ImageService のモック。"""

    async def generate(self, prompt: str, model: str = "", aspect_ratio: str = "16:9", safety_level: str = "general") -> str:
        return "https://example.com/mock_image.png"


class MockPlotExpander:
    """PlotExpander のモック。"""

    async def expand_plots(self, book_id: int, target_ep_list: list[int], arcs: list, reporter: Any = None, force: bool = False, branch_id: int = 1):
        # PlotDetail のリストを返す
        from src.models import PlotDetail
        return [PlotDetail(ep_num=ep, title=f"第{ep}話", one_line_summary="概要", detailed_blueprint="詳細", summary="あらすじ", tension=50, is_catharsis=False, catharsis_type="", next_hook="") for ep in target_ep_list]

    async def expand_single_plot(self, **kwargs):
        from src.models import PlotEpisode
        return PlotEpisode(ep_num=1, title="第1話", detailed_blueprint="詳細", summary="概要", tension=50)


class MockPlotAgent:
    """PlotAgent のモック（run メソッドのみ実装）。"""

    def __init__(self, repo: Any = None, llm: Any = None, prompt_manager: Any = None):
        self.repo = repo
        self.llm = llm
        self.pm = prompt_manager
        self._plot_expander = MockPlotExpander()

    def _ensure_services(self):
        """expand_plots で呼ばれる初期化メソッドのスタブ。"""
        pass

    async def run(self, ctx: Any) -> Any:
        from src.agents.orchestrator import AgentResult, AgentName
        book_id = ctx.book_id
        branch_id = ctx.branch_id
        ep_num = ctx.ep_num
        arcs = ctx.artifacts.get("arcs", [])
        target_eps = ctx.artifacts.get("target_ep_nums", [ep_num])

        try:
            plots = await self._plot_expander.expand_plots(
                book_id=book_id,
                target_ep_list=target_eps,
                arcs=arcs,
                reporter=ctx.artifacts.get("reporter"),
                branch_id=branch_id,
            )
            return AgentResult(
                next_agent=AgentName.BIBLE,
                artifacts={"plots": [p.model_dump() if hasattr(p, "model_dump") else p for p in plots]},
            )
        except Exception as e:
            return AgentResult(
                next_agent=None,
                artifacts={},
                error=f"Plot generation failed: {e}",
            )


class MockWritingAgent:
    """WritingAgent のモック（run メソッドのみ実装）。"""

    def __init__(self, repo: Any = None, llm: Any = None, prompt_manager: Any = None):
        self.repo = repo
        self.llm = llm
        self.pm = prompt_manager

    async def run(self, ctx: Any) -> Any:
        from src.agents.orchestrator import AgentResult, AgentName
        writing_context = ctx.artifacts.get("writing_context")
        if not writing_context:
            return AgentResult(
                next_agent=None,
                artifacts={},
                error="writing_context is required in artifacts",
            )

        book_id = ctx.book_id
        ep_num = ctx.ep_num

        # モック本文を返す
        drafted_text = "モック生成本文です。" * 50
        return AgentResult(
            next_agent=AgentName.AUDIT,
            artifacts={"drafted_text": drafted_text},
        )


class MockAuditAgent:
    """AuditAgent のモック（run メソッドのみ実装）。"""

    def __init__(self, repo: Any = None, llm: Any = None, prompt_manager: Any = None):
        self.repo = repo
        self.llm = llm
        self.pm = prompt_manager

    async def run(self, ctx: Any) -> Any:
        from src.agents.orchestrator import AgentResult, AgentName
        writing_context = ctx.artifacts.get("writing_context")
        drafted_text = ctx.artifacts.get("drafted_text")

        if not writing_context or not drafted_text:
            return AgentResult(
                next_agent=None,
                artifacts={},
                error="writing_context and drafted_text are required in artifacts",
            )

        # 常に合格として返す
        return AgentResult(
            next_agent=AgentName.ILLUSTRATION,
            artifacts={
                "audit_report": {
                    "logical": "passed",
                    "deai": "passed",
                    "ability": "passed",
                    "causal": "passed",
                }
            },
        )


class MockIllustrationAgent:
    """IllustrationAgent のモック（run メソッドのみ実装）。"""

    def __init__(self, repo: Any = None, llm: Any = None, image_service: Any = None):
        self.repo = repo
        self.llm = llm
        self.image_service = image_service

    async def run(self, ctx: Any) -> Any:
        from src.agents.orchestrator import AgentResult, AgentName
        drafted_text = ctx.artifacts.get("drafted_text", "")
        book_context = ctx.artifacts.get("book_context", {})
        book_id = ctx.book_id

        # モックプロンプトを返す
        prompt = f"Illustration prompt for episode {ctx.ep_num} of book {book_id}"
        return AgentResult(
            next_agent=AgentName.MARKETING,
            artifacts={"illustrations": [{"prompt": prompt, "illustration_id": 1}]},
        )


class MockMarketingAgent:
    """MarketingAgent のモック（run メソッドのみ実装）。"""

    def __init__(self, repo: Any = None, llm: Any = None, prompt_manager: Any = None):
        self.repo = repo
        self.llm = llm
        self.pm = prompt_manager

    async def run(self, ctx: Any) -> Any:
        from src.agents.orchestrator import AgentResult
        book_id = ctx.book_id

        # モック ZIP データを返す
        zip_data = b"mock zip data"
        zip_filename = f"export_{book_id}.zip"
        return AgentResult(
            next_agent=None,  # 最後のエージェント
            artifacts={"zip_data": zip_data, "zip_filename": zip_filename},
        )


def create_mock_context(
    book_id: int = 1,
    branch_id: int = 1,
    ep_num: int = 1,
    artifacts: dict[str, Any] | None = None,
):
    """テスト用 AgentContext を作成。"""
    from src.agents.orchestrator import AgentContext

    default_artifacts = {
        "title": "テスト作品",
        "synopsis": "テストあらすじ",
        "target_eps": 10,
        "genre": "fantasy",
        "target_word_count": 3000,
        "repo": MockBookRepository(),
        "llm": MockLLMAdapter(),
        "prompt_manager": MockPromptManager(),
    }
    if artifacts:
        default_artifacts.update(artifacts)

    return AgentContext(
        book_id=book_id,
        branch_id=branch_id,
        ep_num=ep_num,
        artifacts=default_artifacts,
    )


def create_mock_orchestrator(llm: MockLLMAdapter | None = None, repo: MockBookRepository | None = None, prompt_manager: MockPromptManager | None = None):
    """テスト用 Orchestrator を作成（全ノードにモック注入）。"""
    from src.agents import Orchestrator, AgentName
    from src.agents.planning import PlanningAgent
    from src.agents.bible import BibleAgent
    from src.agents.context_builder_agent import ContextBuilderAgent
    from src.services.image_service import ImageService

    llm = llm or MockLLMAdapter()
    repo = repo or MockBookRepository()
    prompt_manager = prompt_manager or MockPromptManager()
    image_service = MockImageService()

    nodes = {
        AgentName.PLANNING: PlanningAgent(repo=repo, llm=llm, prompt_manager=prompt_manager).run,
        AgentName.PLOT: MockPlotAgent(repo=repo, llm=llm, prompt_manager=prompt_manager).run,
        AgentName.BIBLE: BibleAgent(repo=repo, llm=llm, prompt_manager=prompt_manager).run,
        AgentName.CONTEXT_BUILDER: ContextBuilderAgent(repo=repo, llm=llm).run,
        AgentName.WRITING: MockWritingAgent(repo=repo, llm=llm, prompt_manager=prompt_manager).run,
        AgentName.AUDIT: MockAuditAgent(repo=repo, llm=llm, prompt_manager=prompt_manager).run,
        AgentName.ILLUSTRATION: MockIllustrationAgent(repo=repo, llm=llm, image_service=image_service).run,
        AgentName.MARKETING: MockMarketingAgent(repo=repo, llm=llm, prompt_manager=prompt_manager).run,
    }
    return Orchestrator(nodes)