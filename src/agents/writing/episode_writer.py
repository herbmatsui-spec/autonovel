from typing import Any, List

from src.agents.base import BaseAgent
from src.agents.context_builder_agent import ContextBuilderAgent
from src.agents.erotic_enhancer import EroticEnhancer
from src.agents.orchestrator import AgentContext, AgentResult
from src.agents.prompt_composer import PromptComposer
from src.services.llm_service import LLMService
from src.services.rag.context_retriever import ForeshadowingEntity
from prompts.manager import PromptManager


class EpisodeWriter(BaseAgent):
    def __init__(
        self,
        llm: LLMService,
        context_builder: ContextBuilderAgent,
        repo: Any = None,
        style_rag: Any = None,
        rag_prefetch: Any = None,
        context_retriever: Any = None,
        prompt_manager: PromptManager = None,
    ):
        super().__init__(repo=repo, llm=llm, style_rag=style_rag, rag_prefetch=rag_prefetch)
        self.context_builder = context_builder
        self.context_retriever = context_retriever
        self.prompt_manager = prompt_manager

    def detect_resolved_foreshadowings(
        self, content: str, pending_list: List[ForeshadowingEntity]
    ) -> List[str]:
        """生成された本文中から解決された伏線を簡易検知する。
        
        Args:
            content: 生成されたエピソード本文
            pending_list: 現在未回収の伏線リスト
            
        Returns:
            解決されたと判断された伏線のIDリスト
        """
        resolved_ids = []
        if not content or not pending_list:
            return resolved_ids
        
        content_lower = content.lower()
        for fs in pending_list:
            # キーワードのいずれかが本文に含まれているかをチェック
            for keyword in fs.keywords:
                if keyword.lower() in content_lower:
                    resolved_ids.append(fs.foreshadow_id)
                    break  # 1つでもキーワードが見つかったらその伏線は解決とみなす
            # 解決描写の簡易チェック（例: 「解決した」「明らかになった」等）
            # ここではキーワードチェックのみとする
        return resolved_ids

    async def build_context(
        self,
        book_id: int,
        branch_id: int,
        ep_num: int,
        target_word_count: int,
        style_tag: str | None = None,
    ) -> dict[str, Any]:
        """執筆に必要な完全なコンテキストを構築する。"""
        ctx = AgentContext(
            book_id=book_id,
            branch_id=branch_id,
            ep_num=ep_num,
            artifacts={
                "target_word_count": target_word_count,
                "style_tag": style_tag,
            },
        )
        result = await self.context_builder.execute(ctx)
        return result.artifacts.get("writing_context", {})

    async def write(self, book_id: int, ep_num: int, context: dict[str, Any]) -> str:
        """
        エピソード本文を生成し、文字列で返す。
        :param book_id: 書籍ID
        :param ep_num: エピソード番号
        :param context: プロット情報、キャラ設定、世界設定などを含む辞書
        :return: 生成された本文（文字列）
        """
        # プロンプトを構築
        prompt_composer = PromptComposer(self)
        prompt = await prompt_composer.compose_writing_prompt(book_id, ep_num, context)

        # 初期結果を生成
        result = await self.llm.generate_text(
            purpose="writing",
            prompt=prompt,
            system_instruction=None,
            temperature=0.7,
        )
        if hasattr(result, "story_content"):
            result = result.story_content

        # エロティックコンテンツを強化
        erotic_enhancer = EroticEnhancer(self)
        result = erotic_enhancer.enhance_erotic_content(prompt, result, context)

        return str(result)

    async def run(self, ctx: AgentContext) -> AgentResult:
        """エージェント固有のメインロジック。サブクラスで実装する。"""
        book_id = ctx.book_id
        ep_num = ctx.ep_num
        # The writing context should be in the artifacts from the context_builder_agent
        writing_context = ctx.artifacts.get("writing_context", {})
        # Generate the written text
        written_text = await self.write(book_id, ep_num, writing_context)
        # Return the result with the written text in artifacts
        return AgentResult(
            next_agent=None,
            artifacts={"written_text": written_text},
            should_retry=False,
            error=None,
        )