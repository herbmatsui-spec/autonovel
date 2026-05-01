"""
engine.py - 覇権AIエンジンコアモジュール
Gemini API との対話、プロット生成、本文執筆の全ロジックを集約。
UltimateHegemonyEngine が全機能を統合する。
"""
from __future__ import annotations
import json
import asyncio
import logging
import datetime
import random
import re
import time
import threading
from typing import Any, Dict, List, Optional, Tuple, Union, Callable
from google import genai # type: ignore
from google.genai import types as genai_types
from jinja2 import Environment, DictLoader
from pydantic import ValidationError

logger = logging.getLogger(__name__)

# サブモジュールと定数のインポート
from engine_utils import AdaptiveCooldown, safe_run_async, is_light_style, safe_model_validate
from engine_prompts import PromptManager, get_rule_set
from engine_context import ContextManager
from engine_narrative import NarrativeController
from engine_critique import CritiqueAgent
from engine_agents import LogicalAuditor, MarketingAgent, PlanningAgent, WritingAgent
from config import (
    STYLE_DEFINITIONS, PROMPT_TEMPLATES, MODEL_PLANNING, MODEL_STABLE_FALLBACK,
    COOLDOWN_BASE_DEFAULT, COOLDOWN_MIN_DEFAULT, COOLDOWN_MAX_DEFAULT
)
from models import (
    WorldBible, GenerateResult, CharacterRegistry, WorldRules, 
    WorldBibleCore, RoadmapList, PlotEpisode, HegemonyAuditResult, 
    EpisodeDraft, PlotDbModel, WorldState
)
from database import DataRepository, get_db_manager, DatabaseManager
from sanitizer import TextFormatter, OutputSanitizer

# ==========================================
# GeminiApiClient (AI通信の責務を分離)
# ==========================================
class GeminiApiClient:
    """
    Google GenAI SDKとの低レベル通信を担当。
    リトライ、指数バックオフ、温度減衰、エラーハンドリングを集約。
    """
    def __init__(self, client: genai.Client, cooldown: AdaptiveCooldown):
        self.client = client
        self.cooldown = cooldown
        self._active_requests = 0  # 現在の並行実行数を追跡

    async def generate_json(
        self,
        model_name: str,
        prompt: str,
        system_instruction: Optional[str] = None,
        response_schema: Any = None,
        temp: float = 0.7,
        max_retries: int = 5,
        stream_callback: Optional[Callable[[str], None]] = None
    ) -> Tuple[Dict[str, Any], str, Any]:
        error_feedback = ""
        current_max_retries = max_retries
        prompt_len = len(prompt)
        
        for attempt in range(max_retries):
            # リクエスト前に能動的に待機（スロットリング）を実行
            await self.cooldown.wait()

            start_time = time.time()
            self._active_requests += 1
            
            try:
                current_system_instruction = system_instruction
                config = self.build_config(current_system_instruction, temp, attempt, response_schema)
                
                # プロンプト構築（スキーマ要求とエラーフィードバックの注入）
                full_prompt = prompt
                if error_feedback:
                    full_prompt = f"【🚨出力形式エラー報告🚨】\n前回の出力に以下の不備がありました: {error_feedback}\n\n{prompt}"
                
                if response_schema and hasattr(response_schema, "model_fields"):
                    fields = list(response_schema.model_fields.keys())
                    full_prompt += f"\n\n※重要: JSONには以下のキーを必ず含めてください: {', '.join(fields)}"
                    full_prompt += "\n\nCRITICAL: Output MUST be valid JSON ONLY. Start with '{' and end with '}'."

                full_text = ""
                usage = None

                # ストリーミング対応
                if stream_callback:
                    response_stream = self.client.models.generate_content_stream(
                        model=model_name, contents=[full_prompt], config=config
                    )
                    for chunk in response_stream:
                        if chunk.text:
                            full_text += chunk.text
                            stream_callback(chunk.text)
                        if chunk.usage_metadata:
                            usage = chunk.usage_metadata
                else:
                    def _call():
                        return self.client.models.generate_content(
                            model=model_name, contents=[full_prompt], config=config
                        )
                    response = await asyncio.to_thread(_call)
                    if not response or not response.text:
                        raise ValueError("API応答が空です。")
                    
                    duration = time.time() - start_time
                    full_text = response.text
                    usage = getattr(response, 'usage_metadata', None)

                metadata, story = OutputSanitizer.extract_content_and_metadata(full_text)
                
                # Schema Validation
                if response_schema and hasattr(response_schema, "model_validate"):
                    try:
                        safe_model_validate(response_schema, metadata)
                    except ValidationError as ve:
                        error_feedback = OutputSanitizer.format_validation_error(ve)
                        logger.warning(f"Validation failed (Attempt {attempt+1}): {error_feedback}")
                        if attempt == max_retries - 1:
                            raise ve
                        # 次回リトライのために温度を下げる
                        temp = max(0.0, temp - 0.1)
                        continue
                
                self.cooldown.on_success()
                logger.info(f"✅ API Success: model={model_name}, len={prompt_len}, dur={duration:.2f}s, parallel={self._active_requests}")
                return metadata, story, usage

            except Exception as e:
                duration = time.time() - start_time
                err_msg = str(e)
                
                # 診断ログの出力
                diag_info = (
                    f"\n[API DIAGNOSTIC]\n"
                    f"- Model: {model_name}\n"
                    f"- Prompt Length: {prompt_len} chars\n"
                    f"- Duration until error: {duration:.2f}s\n"
                    f"- Parallel Requests: {self._active_requests}\n"
                    f"- Attempt: {attempt + 1}/{max_retries}\n"
                    f"- Error: {err_msg}"
                )
                logger.warning(f"❌ API Error Details: {diag_info}")

                # 503 エラーが続く場合、中盤以降のリトライで安定モデルに切り替える
                current_model = model_name
                if (attempt >= 2 or (attempt == 0 and "-preview" in model_name)) and "503" in str(e): # 初回503でプレビューモデルなら即座にフォールバック
                    logger.warning(f"🚨 503継続のため安定モデル {MODEL_STABLE_FALLBACK} へ切り替えます。")
                    current_model = MODEL_STABLE_FALLBACK
                
                # 503エラー発生時は、エンジンのセマフォを一時的に絞るシグナルを出す（動的並列抑制）
                if "503" in str(e) and hasattr(self.cooldown, "on_rate_limit"):
                    logger.info("📉 503エラーにより並列リクエストを抑制します。")
                    self.cooldown.on_rate_limit()

                if not await self._handle_error(e, current_model, attempt, max_retries):
                    self._active_requests -= 1
                    raise e
                
                # リトライ時はモデル名を更新して次ループへ
                model_name = current_model
            finally:
                self._active_requests -= 1

        raise RuntimeError("Max retries exceeded")

    def build_config(self, system_instruction: Optional[str], temp: float, attempt: int, response_schema: Any = None) -> genai_types.GenerateContentConfig:
        # リトライごとに温度を下げることで、AIの迷走を抑える
        current_temp = max(0.0, temp - (attempt * 0.15))
        config = genai_types.GenerateContentConfig(
            temperature=current_temp,
            system_instruction=system_instruction,
        )
        if response_schema:
            config.response_mime_type = "application/json"
        return config

    async def _handle_error(self, e: Exception, model_name: str, attempt: int, max_retries: int) -> bool:
        err_msg = str(e).lower() # type: ignore
        if any(x in err_msg for x in ["429", "quota", "503", "unavailable", "500", "502", "internal", "bad gateway"]):
            retry_match = re.search(r'retry\s+in\s+([\d\.]+)', err_msg) # Google APIからの具体的な待機指示を優先
            # 指定がない場合は待機時間 0 で即座にリトライ
            base_wait = float(retry_match.group(1)) if retry_match else 0.0
            wait_time = min(base_wait, 60.0)
            logger.warning(f"Retrying (Attempt {attempt+1}) after {wait_time:.1f}s due to API congestion. Backoff: OFF")
            self.cooldown.on_rate_limit()
            await asyncio.sleep(wait_time)
            return True
        return False

# ==========================================
# UltimateHegemonyEngine（メインエンジン）
# ==========================================
class UltimateHegemonyEngine:
    """覇権小説自動生成エンジン v2.0"""

    def __init__(self, api_key: str, client: Optional[genai.Client] = None, db_manager: Optional[DatabaseManager] = None):
        self.api_key    = api_key
        self.client     = client or genai.Client(api_key=api_key)
        self.cooldown   = AdaptiveCooldown(
            base_sec=COOLDOWN_BASE_DEFAULT,
            min_sec=COOLDOWN_MIN_DEFAULT,
            max_sec=COOLDOWN_MAX_DEFAULT
        )
        # Python 3.14+ 対策: スレッドごとに独立した Semaphore 保持領域を確保。
        # これにより、別ループの Semaphore に触れる（比較する）こと自体を物理的に回避する。
        self._local     = threading.local()
        self.ai_api     = GeminiApiClient(self.client, self.cooldown)
        self.current_ep_num = 0
        
        self.db         = db_manager or get_db_manager()
        self.repo       = DataRepository(self.db)
        self.jinja_env  = Environment(loader=DictLoader(PROMPT_TEMPLATES))
        self.pm         = PromptManager(self.jinja_env)
        self.ctx_mgr    = ContextManager(self.repo)
        self.auditor    = LogicalAuditor(self)
        self.narrative  = NarrativeController(self)
        self.critique   = CritiqueAgent(self)
        self.marketing  = MarketingAgent(self)
        self.formatter  = TextFormatter()
        self.planner    = PlanningAgent(self)
        self.writer     = WritingAgent(self)

    def _is_light_style(self, style_key: str, genre: str) -> bool: # type: ignore
        """スタイルまたはジャンルから、コミカル/ライトな作風かを一元判定する"""
        return is_light_style(style_key, genre)

    def _safe_update_token_stats(self, prompt: int, completion: int, reporter: Any = None) -> None:
        """
        スレッドセーフにトークン統計を更新する。
        """
        try:
            # reporter (ProgressState) 経由での更新を優先
            if reporter and hasattr(reporter, "state"):
                reporter.state.token_usage["prompt"] += prompt
                reporter.state.token_usage["completion"] += completion
                reporter.state.token_usage["calls"] += 1
        except (AttributeError, RuntimeError, KeyError):
            # セッションコンテキストがない場合はログ出力のみに留める
            logger.debug(f"Token stats update skipped (No session context): prompt={prompt}, completion={completion}")

    def _get_loop_bound_semaphore(self, name: str, default_value: int) -> asyncio.Semaphore:
        """Returns a semaphore bound to the current running event loop, recreating it if the loop has changed."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            raise RuntimeError("No running event loop detected.")

        # Check thread-local storage for a semaphore and its associated loop
        stored_loop = getattr(self._local, f"{name}_loop", None)
        
        # Recreate if: not exists, loop identity changed, or loop is closed (stale reference)
        if not hasattr(self._local, name) or stored_loop is not loop or (stored_loop and stored_loop.is_closed()):
            # Explicitly create the semaphore in the current loop context
            setattr(self._local, name, asyncio.Semaphore(default_value))
            setattr(self._local, f"{name}_loop", loop)
            logger.debug(f"Created new loop-bound semaphore: {name} (value={default_value})")
            
        return getattr(self._local, name)

    # ------ Core API ------
    async def _generate_json(
        self,
        model_name: str,
        prompt: str,
        response_schema: Any = None,
        system_instruction: Optional[str] = None,
        temp: float = 0.7,
        expected_ep_num: Optional[int] = None,
        stream_callback: Optional[Callable[[str], None]] = None,
    ) -> GenerateResult:
        """Gemini API 呼び出しのコア"""
        try:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                return GenerateResult(success=False, error_type="LOOP_ERROR", error_message="No running event loop")

            # スレッドローカル内でも「現在のループ」専用のセマフォのみを扱うよう絶縁
            if not hasattr(self._local, "sems"):
                self._local.sems = {}
            
            if loop not in self._local.sems or loop.is_closed():
                max_conc = 8 # または config から取得
                self._local.sems[loop] = asyncio.Semaphore(max_conc)

            async with self._local.sems[loop]:
                # 通信とリトライ、エラーハンドリングを GeminiApiClient に一任
                metadata, story_content, usage = await self.ai_api.generate_json(
                    model_name, prompt,
                    system_instruction=system_instruction,
                    response_schema=response_schema,
                    temp=temp,
                    stream_callback=stream_callback
                )

                if expected_ep_num and metadata.get("ep_num") != expected_ep_num:
                    metadata["ep_num"] = expected_ep_num

                if usage:
                    reporter_obj = getattr(stream_callback, "__self__", None)
                    self._safe_update_token_stats(
                        getattr(usage, 'prompt_token_count', 0), 
                        getattr(usage, 'candidates_token_count', 0), 
                        reporter=reporter_obj
                    )

                return GenerateResult(success=True, metadata=metadata, story_content=story_content)

        except Exception as e:
            try:
                err_msg = str(e)
            except Exception:
                err_msg = "API Error (Loop Mismatch in Exception Stringification)"
            return GenerateResult(success=False, error_type="API_ERROR", error_message=err_msg)

    # NOTE: 冗長な移譲メソッド（create_hegemony_plan, save_plan_to_db, 
    # generate_episodes, generate_marketing_pack等）は削除し、
    # HegemonyService 等から self.planner, self.writer を直接参照することを推奨。
    # ------ Plot Expansion ------
    async def _expand_plots_1_by_1(
        self,
        book_id: int,
        target_ep_list: List[int],
        arcs: List[Any],
        reporter=None,
        **kwargs,
    ) -> List[Any]:
        """PlanningAgentにプロット展開を移譲（機能統合）"""
        return await self.planner.expand_plots(
            book_id=book_id,
            target_ep_list=target_ep_list,
            arcs=arcs,
            reporter=reporter
        )

    # ------ Episode Writing ------

    # ==========================================
    def _get_dynamic_hate_gain(self, genre: str) -> int:
        """NarrativeControllerに移譲"""
        return self.narrative.get_dynamic_hate_gain(genre)

    async def _compute_stress_phase(
        self,
        book_id: int,
        ep_num: int,
        plot: Any,
        current_stress: int,
        genre: str = "default",
        reporter=None,
    ) -> Tuple[str, bool, int]:
        """NarrativeControllerに移譲"""
        res = self.narrative.compute_stress_phase(
            ep_num=ep_num,
            current_stress=current_stress,
            is_planned_catharsis=plot.is_catharsis,
            genre=genre
        )
        return res["instruction"], res["force_catharsis"], res["next_stress"]

    async def generate_episodes(
        self,
        book_id: int,
        start_ep: int,
        end_ep: int,
        passion: float = 0.5,
        target_word_count: int = 2500,
        do_refine: bool = True,
        reporter=None,
        env_state: Optional[Dict[str, str]] = None,
        is_easy_mode: bool = False,
    ) -> int:
        """WritingAgentに本文執筆を移譲"""
        return await self.writer.generate_episodes(
            book_id=book_id,
            start_ep=start_ep,
            end_ep=end_ep,
            passion=passion,
            target_word_count=target_word_count,
            do_refine=do_refine,
            reporter=reporter,
            env_state=env_state,
            is_easy_mode=is_easy_mode
        )

    # ------ Pipeline ------
    async def generate_episodes_pipeline(
        self,
        book_id: int,
        start_ep: int,
        end_ep: int,
        passion: float = 0.5,
        target_word_count: int = 2500,
        reporter=None,
        is_easy_mode: bool = False,
    ) -> int:
        """WritingAgentにパイプライン執筆を移譲"""
        return await self.writer.generate_episodes_pipeline(
            book_id=book_id,
            start_ep=start_ep,
            end_ep=end_ep,
            passion=passion,
            target_word_count=target_word_count,
            reporter=reporter,
            is_easy_mode=is_easy_mode
        )

    # ------ AIプロデューサー診断 ------
    async def audit_producer_plan(self, genre: str, keywords: str, trend_memo: str) -> Optional[HegemonyAuditResult]:
        """PlanningAgentに委譲してロジックを一元化"""
        return await self.planner.audit_producer_plan(genre, keywords, trend_memo)

    # ------ マーケティング生成 ------
    async def generate_marketing_pack(self, book_id: int, latest_ep: int) -> Optional[Dict[str, Any]]:
        """MarketingAgentに移譲"""
        book = await self.repo.get_book(book_id)
        if not book: return None
        return await self.marketing.generate_marketing_pack(book.title, book.synopsis, latest_ep)

    # ------ タイトル生成 ------
    async def generate_title_suggestions(self, genre: str, keywords: str) -> List[str]:
        """MarketingAgentに移譲"""
        return await self.marketing.generate_titles(genre, keywords)

    async def extract_style_dna(self, sample_text: str) -> Dict[str, Any]:
        """MarketingAgentに移譲"""
        return await self.marketing.analyze_style_dna(sample_text)

    # ------ 本文インポート（解析付き） ------
    async def analyze_and_import_chapter(
        self, book_id: int, ep_num: int, content: str, do_refine: bool = False
    ) -> Dict[str, Any]:
        """WritingAgentに移譲"""
        return await self.writer.analyze_and_import_chapter(book_id, ep_num, content, do_refine)

    async def import_chapter_direct_parse(self, book_id: int, ep_num: int, full_text: str, do_refine: bool = False) -> Dict[str, Any]:
        """JSONが混在したテキストから本文を分離してインポートする（OutputSanitizerを活用）"""
        metadata, content_text = OutputSanitizer.extract_content_and_metadata(full_text)
        # If metadata was extracted, it means the JSON was found and separated.
        # We can then proceed with the cleaned content.
        return await self.writer.analyze_and_import_chapter(book_id, ep_num, content_text, do_refine=do_refine)