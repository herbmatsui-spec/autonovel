"""上級者エディタ支援（インラインAI・五感拡張）サービスモジュール."""
from __future__ import annotations

import logging

from src.core.llm_gateway import LLMGateway
from src.engine.prompts.editor_prompts import (
    EDITOR_SYSTEM_INSTRUCTION,
    EXPAND_GENERAL_PROMPT,
    SENSORY_PROMPTS,
    SHOW_DONT_TELL_PROMPT,
    TONE_PROMPTS,
)
from src.models.editor import (
    AssistAction,
    AssistRequest,
    AssistResponse,
    SensoryType,
    ToneType,
)

logger = logging.getLogger(__name__)


class EditorAssistService:
    """インライン AI アシスト（五感描写拡張・Show Don't Tell・トーン書き換え）サービス"""

    def __init__(self, llm_gateway: LLMGateway | None = None):
        self.llm = llm_gateway or LLMGateway()

    async def assist(self, request: AssistRequest) -> AssistResponse:
        """リクエストのアクション種別に応じて適切な拡張・推敲を実行する"""
        if request.action == AssistAction.DESCRIBE:
            stype = request.sensory_type or SensoryType.VISUAL
            res_text = await self.expand_sensory(
                text=request.text,
                sensory_type=stype,
                genre=request.genre,
                context_before=request.context_before,
                context_after=request.context_after,
                custom_instruction=request.custom_instruction,
            )
            diff = f"五感描写（{stype.value}）を拡張"
        elif request.action == AssistAction.SHOW_DONT_TELL:
            res_text = await self.show_dont_tell(
                text=request.text,
                genre=request.genre,
                context_before=request.context_before,
                context_after=request.context_after,
                custom_instruction=request.custom_instruction,
            )
            diff = "感情・状況を情景描写（Show, Don't Tell）に変換"
        elif request.action == AssistAction.REWRITE:
            ttype = request.tone_type or ToneType.TENSION
            res_text = await self.rewrite_tone(
                text=request.text,
                tone_type=ttype,
                genre=request.genre,
                context_before=request.context_before,
                context_after=request.context_after,
                custom_instruction=request.custom_instruction,
            )
            diff = f"トーン（{ttype.value}）に書き換え"
        else:
            # EXPAND
            res_text = await self.expand_general(
                text=request.text,
                genre=request.genre,
                context_before=request.context_before,
                context_after=request.context_after,
                custom_instruction=request.custom_instruction,
            )
            diff = "本文内容を詳細に肉付け拡張"

        return AssistResponse(
            original_text=request.text,
            result_text=res_text.strip(),
            action=request.action,
            diff_summary=diff,
        )

    async def expand_sensory(
        self,
        text: str,
        sensory_type: SensoryType,
        genre: str = "ハイファンタジー (R15)",
        context_before: str = "",
        context_after: str = "",
        custom_instruction: str = "",
    ) -> str:
        """指定された五感（視覚・聴覚・嗅覚・触覚・味覚・比喩）を肉付けする"""
        prompt_tmpl = SENSORY_PROMPTS.get(sensory_type, SENSORY_PROMPTS[SensoryType.VISUAL])
        prompt = prompt_tmpl.format(text=text)
        if custom_instruction:
            prompt += f"\n追加指示: {custom_instruction}"
        return await self._call_llm(prompt, genre, context_before, context_after)

    async def show_dont_tell(
        self,
        text: str,
        genre: str = "ハイファンタジー (R15)",
        context_before: str = "",
        context_after: str = "",
        custom_instruction: str = "",
    ) -> str:
        """感情・状況説明を情景・行動描写に変換する"""
        prompt = SHOW_DONT_TELL_PROMPT.format(text=text)
        if custom_instruction:
            prompt += f"\n追加指示: {custom_instruction}"
        return await self._call_llm(prompt, genre, context_before, context_after)

    async def rewrite_tone(
        self,
        text: str,
        tone_type: ToneType,
        genre: str = "ハイファンタジー (R15)",
        context_before: str = "",
        context_after: str = "",
        custom_instruction: str = "",
    ) -> str:
        """指定されたトーン（緊迫・官能・テンポ等）に文体を書き換える"""
        prompt_tmpl = TONE_PROMPTS.get(tone_type, TONE_PROMPTS[ToneType.TENSION])
        prompt = prompt_tmpl.format(text=text)
        if custom_instruction:
            prompt += f"\n追加指示: {custom_instruction}"
        return await self._call_llm(prompt, genre, context_before, context_after)

    async def expand_general(
        self,
        text: str,
        genre: str = "ハイファンタジー (R15)",
        context_before: str = "",
        context_after: str = "",
        custom_instruction: str = "",
    ) -> str:
        """テキストを自然に展開・肉付けする"""
        c_inst = f"追加指示: {custom_instruction}" if custom_instruction else ""
        prompt = EXPAND_GENERAL_PROMPT.format(text=text, custom_instruction=c_inst)
        return await self._call_llm(prompt, genre, context_before, context_after)

    async def _call_llm(
        self,
        prompt: str,
        genre: str,
        context_before: str = "",
        context_after: str = "",
    ) -> str:
        """LLM を呼び出してテキストを生成する"""
        sys_inst = f"{EDITOR_SYSTEM_INSTRUCTION}\n作品ジャンル: {genre}"
        if context_before:
            prompt = f"【直前の文脈】\n{context_before[-300:]}\n\n{prompt}"
        if context_after:
            prompt = f"{prompt}\n\n【直後の文脈】\n{context_after[:300]}"

        try:
            res = await self.llm.generate_text(
                purpose_or_request="writing",
                prompt=prompt,
                system_instruction=sys_inst,
                temp=0.7,
            )
            content = getattr(res, "story_content", "") or ""
            if not content and hasattr(res, "content"):
                content = res.content
            return str(content) if content else "（拡張テキストの生成に失敗しました）"
        except Exception as e:
            logger.error("EditorAssistService LLM call failed: %s", e)
            # フォールバックとして簡易修飾
            return f"{prompt.splitlines()[-1]}（詳細な情景が静かに広がっていく）"
