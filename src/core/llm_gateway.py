from __future__ import annotations

import asyncio
import json
import re
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from google import genai  # type: ignore
from google.genai import types as genai_types

from src.backend.engine_utils import AdaptiveCooldown, safe_model_validate
from src.backend.sanitizer import OutputSanitizer
from src.core.exceptions import LLMUnrecoverableError
from src.core.observability import StructuredLogger
from src.models.base import get_gemini_schema
from src.services.retry_decorator import RetryState, with_llm_retry

logger = StructuredLogger(__name__)

def create_genai_client(api_key: str):
    """Gemini API クライアントを作成する"""
    from google import genai
    return genai.Client(api_key=api_key)

class LLMProviderFactory:
    """LLMプロバイダの抽象化"""
    def __init__(self, genai_client, cooldown):
        self.genai_client = genai_client
        self.cooldown = cooldown

    def get_client(self, provider: str = "gemini"):
        """モデル名から適切なAPIクライアントを返す。

        OpenRouter 等の OpenAI互換モデルID ("anthropic/claude-3.5-sonnet" 等)
        や、gpt/claude/llama 等のキーワードを含む場合は OpenAI 互換クライアントを返す。
        """
        from src.llm.model_router import is_openai_compatible

        if is_openai_compatible(provider):
            return OpenAIApiClient(cooldown=self.cooldown)

        provider_key = provider.split("-")[0] if "-" in provider else provider
        if provider_key == "gemini":
            return GeminiApiClient(client=self.genai_client, cooldown=self.cooldown)
        # デフォルトは Gemini
        return GeminiApiClient(client=self.genai_client, cooldown=self.cooldown)

    def get_available_providers(self) -> List[str]:
        """Get list of available providers"""
        providers = []
        if self.genai_client:
            providers.append("gemini")
        try:
            import openai  # noqa: F401
            providers.append("openai")
        except ImportError:
            pass
        return providers

class SemanticCacheManager:
    """意味的キャッシュマネージャ"""
    def __init__(self, vector_store=None):
        self.vector_store = vector_store

    def get(self, key: str):
        try:
            if self.vector_store and hasattr(self.vector_store, 'get'):
                return self.vector_store.get(key)
            return None
        except Exception as e:
            logger.warning(f"Cache get failed for key={key}: {e}")
            return None

    def set(self, key: str, value: Any, ttl: int = 3600):
        try:
            if self.vector_store and hasattr(self.vector_store, 'set'):
                self.vector_store.set(key, value, ttl)
        except Exception as e:
            logger.warning(f"Cache set failed for key={key}: {e}")

class LLMGenerateResultProxy:
    """LLM生成結果のプロキシ"""
    def __init__(self, llm_factory=None, factory=None):
        self.llm_factory = llm_factory or factory

    def get_client(self, model_name: str = "gemini"):
        return self.llm_factory.get_client(model_name)

    @staticmethod
    def _normalize_response(response: Any) -> Any:
        class _Response:
            def __init__(self, success: bool, content: Any = None, metadata: Any = None, usage: Any = None):
                self.success = success
                self.content = content
                self.metadata = metadata
                self.usage = usage
        if isinstance(response, tuple):
            if len(response) == 2:
                content, usage = response
                return _Response(success=True, content=content, usage=usage)
            if len(response) == 3:
                metadata, content, usage = response
                return _Response(success=True, content=content, metadata=metadata, usage=usage)
        return response

    @staticmethod
    def _usage_metric(usage: Any, key: str, default: int = 0) -> int:
        if usage is None:
            return default
        if isinstance(usage, dict):
            return usage.get(key, default)
        return getattr(usage, key, default)

    async def generate_json(self, *args, **kwargs):
        is_request_obj = False
        if args and not isinstance(args[0], str):
            request = args[0]
            is_request_obj = True
        elif 'request' in kwargs:
            request = kwargs['request']
            is_request_obj = True
        
        if is_request_obj:
            provider = self.get_client(request.model_name)
            response = await provider.generate_json(
                model_name=request.model_name,
                prompt=request.prompt,
                response_schema=request.response_schema,
                system_instruction=request.system_instruction,
                temp=request.temp
            )
            response = self._normalize_response(response)
            class GenerateResult(dict):
                def __init__(self, response):
                    super().__init__()
                    self["success"] = response.success
                    self["metadata"] = response.metadata
                    self["story_content"] = response.content
                    self["token_usage"] = {
                        "prompt": LLMGenerateResultProxy._usage_metric(response.usage, "prompt_tokens", 0),
                        "completion": LLMGenerateResultProxy._usage_metric(response.usage, "completion_tokens", 0),
                        "calls": 1
                    }
                @property
                def success(self): return self["success"]
                @property
                def metadata(self): return self["metadata"]
                @property
                def story_content(self): return self["story_content"]
                @property
                def token_usage(self): return self["token_usage"]
            return GenerateResult(response)
        else:
            from src.llm.model_router import resolve_model
            purpose = args[0] if len(args) > 0 else kwargs.get('purpose')
            prompt = args[1] if len(args) > 1 else kwargs.get('prompt')
            response_schema = args[2] if len(args) > 2 else kwargs.get('response_schema')
            system_instruction = args[3] if len(args) > 3 else kwargs.get('system_instruction')
            model_name = resolve_model(purpose)
            
            provider = self.get_client(model_name)
            response = await provider.generate_json(
                model_name=model_name,
                prompt=prompt,
                response_schema=response_schema,
                system_instruction=system_instruction,
                temp=kwargs.get('temp', 0.7)
            )
            return {
                "success": response.success,
                "metadata": response.metadata,
                "story_content": response.content,
                "token_usage": {
                    "prompt": response.usage.get("prompt_tokens", 0) if response.usage else 0,
                    "completion": response.usage.get("completion_tokens", 0) if response.usage else 0,
                    "calls": 1
                }
            }

    async def generate_text(self, *args, **kwargs):
        is_request_obj = False
        if args and not isinstance(args[0], str):
            request = args[0]
            is_request_obj = True
        elif 'request' in kwargs:
            request = kwargs['request']
            is_request_obj = True
            
        if is_request_obj:
            provider = self.get_client(request.model_name)
            response = await provider.generate_text(
                model_name=request.model_name,
                prompt=request.prompt,
                system_instruction=request.system_instruction,
                temp=request.temp
            )
            response = self._normalize_response(response)
            class GenerateResult(dict):
                def __init__(self, response):
                    super().__init__()
                    self["success"] = response.success
                    self["story_content"] = response.content
                    self["token_usage"] = {
                        "prompt": LLMGenerateResultProxy._usage_metric(response.usage, "prompt_tokens", 0),
                        "completion": LLMGenerateResultProxy._usage_metric(response.usage, "completion_tokens", 0),
                        "calls": 1
                    }
                @property
                def success(self): return self["success"]
                @property
                def story_content(self): return self["story_content"]
                @property
                def token_usage(self): return self["token_usage"]
            return GenerateResult(response)
        else:
            from src.llm.model_router import select_model
            purpose = args[0] if len(args) > 0 else kwargs.get('purpose')
            prompt = args[1] if len(args) > 1 else kwargs.get('prompt')
            system_instruction = args[2] if len(args) > 2 else kwargs.get('system_instruction')
            model_name = select_model(purpose)
            
            provider = self.get_client(model_name)
            response = await provider.generate_text(
                model_name=model_name,
                prompt=prompt,
                system_instruction=system_instruction,
                temp=kwargs.get('temp', 0.7)
            )
            return response.content

    def generate(self, *args, **kwargs):
        logger.debug("LLMGenerateResultProxy.generate() called - returning empty placeholder")
        return {}, "", None

class GeminiApiClient:
    """
    Google GenAI SDKとの低レベル通信を担当。
    リトライ、指数バックオフ、温度減衰、エラーハンドリングを集約。
    """
    def __init__(self, client: genai.Client, cooldown: AdaptiveCooldown):
        self.client = client
        self.cooldown = cooldown
        self._active_requests = 0  # 現在の並行実行数を追跡

    @with_llm_retry()
    async def generate_json(
        self,
        model_name: str,
        prompt: str,
        system_instruction: Optional[str] = None,
        response_schema: Any = None,
        temp: float = 0.7,
        max_retries: int = 5,
        stream_callback: Optional[Callable[[str], None]] = None,
        retry_state: Optional[RetryState] = None,
        nsfw_mode: bool = False
    ) -> Tuple[Dict[str, Any], str, Any]:
        # リトライ状態から現在のパラメータを取得
        current_temp = retry_state.temp
        current_model = retry_state.model_name
        error_feedback = retry_state.error_feedback
        attempt = retry_state.attempt

        start_time = time.time()

        # スキーマフォールバックモードの定義
        schema_modes = ["native", "clean_dict", "prompt_fallback"]
        if not response_schema:
            schema_modes = ["prompt_fallback"]

        last_error = None
        full_text = ""
        usage = None

        for mode in schema_modes:
            config = self.build_config_for_mode(system_instruction, current_temp, attempt, response_schema, mode, nsfw_mode=nsfw_mode)

            # プロンプト構築（スキーマ要求とエラーフィードバックの注入）
            full_prompt = prompt
            if error_feedback:
                full_prompt = f"【🚨出力形式エラー報告🚨】\n前回の出力に以下の不備がありました: {error_feedback}\n\n{prompt}"

            if response_schema:
                if mode == "prompt_fallback":
                    schema_dict = get_gemini_schema(response_schema)
                    schema_json = json.dumps(schema_dict, ensure_ascii=False, indent=2)
                    full_prompt += f"\n\n【出力スキーマ指示】\n以下のJSONスキーマ構造に完全に従って、JSONオブジェクトのみを出力してください。余計なマークダウンや説明は一切不要です。\n```json\n{schema_json}\n```"
                elif hasattr(response_schema, "model_fields"):
                    fields = list(response_schema.model_fields.keys())
                    full_prompt += f"\n\n※重要: JSONには以下のキーを必ず含めてください: {', '.join(fields)}"
                full_prompt += "\n\nCRITICAL: Output MUST be valid JSON ONLY. Start with '{' and end with '}'."

            full_text = ""
            usage = None

            try:
                # ストリーミング対応
                if stream_callback:
                    response_stream = self.client.models.generate_content_stream(
                        model=current_model, contents=[full_prompt], config=config
                    )
                    for chunk in response_stream:
                        if chunk.text:
                            full_text += chunk.text
                            stream_callback(chunk.text)
                        if chunk.usage_metadata:
                            usage = chunk.usage_metadata
                else:
                    def _call():
                        # 404 NOT_FOUND 回避のため、モデル名に 'models/' プレフィックスが付いていない場合は付与する
                        model_with_prefix = current_model if current_model.startswith('models/') else f'models/{current_model}'
                        return self.client.models.generate_content(
                            model=model_with_prefix, contents=[full_prompt], config=config
                        )
                    try:
                        from src.core.async_utils import safe_timeout
                        from src.core.executor_manager import executor_manager
                        async with safe_timeout(120.0):
                            response = await executor_manager.run_io(_call)
                    except asyncio.TimeoutError as e:
                        raise TimeoutError(f"Gemini API timed out after 120s: {e}")
                    if not response or not response.text:
                        raise ValueError("API応答が空です。")

                    full_text = response.text
                    usage = getattr(response, 'usage_metadata', None)

                # 成功したらループを抜け出す
                last_error = None
                break
            except Exception as e:
                err_msg = str(e).lower()
                is_schema_error = any(x in err_msg for x in ["schema", "invalid argument", "bad request", "400", "properties", "additionalproperties"])
                if is_schema_error and mode != "prompt_fallback":
                    logger.warning(f"Gemini API schema error with mode '{mode}' (attempt={attempt}): {e}. Falling back to next schema mode.")
                    last_error = e
                    continue
                else:
                    raise e

        if last_error:
            raise last_error

        metadata, story = OutputSanitizer.extract_content_and_metadata(full_text)

        # Schema Validation
        if response_schema and hasattr(response_schema, "model_validate"):
            safe_model_validate(response_schema, metadata)

        duration = time.time() - start_time
        logger.info(f"✅ API Success: model={current_model}, len={len(prompt)}, dur={duration:.2f}s, parallel={self._active_requests}")
        return metadata, story, usage

    @with_llm_retry()
    async def generate_text(
        self,
        model_name: str,
        prompt: str,
        system_instruction: Optional[str] = None,
        temp: float = 0.7,
        max_retries: int = 5,
        stream_callback: Optional[Callable[[str], None]] = None,
        retry_state: Optional[RetryState] = None,
        nsfw_mode: bool = False
    ) -> Tuple[str, Any]:
        current_temp = retry_state.temp
        current_model = retry_state.model_name

        start_time = time.time()
        config = self.build_config_for_mode(system_instruction, current_temp, retry_state.attempt, None, "native", nsfw_mode=nsfw_mode)

        try:
            from src.core.async_utils import safe_timeout

            if stream_callback:
                # ストリーミングは同期ジェネレータのため、別スレッドで実行して
                # イベントループをブロックしないようにする（google-genai SDK に
                # *_async メソッドは存在しない）。
                def _run_stream():
                    collected: List[str] = []
                    last_usage = None
                    # 404 NOT_FOUND 回避のため、モデル名に 'models/' プレフィックスが付いていない場合は付与する
                    model_with_prefix = current_model if current_model.startswith('models/') else f'models/{current_model}'
                    for chunk in self.client.models.generate_content_stream(
                        model=model_with_prefix,
                        contents=[prompt],
                        config=config,
                    ):
                        if getattr(chunk, "text", None):
                            collected.append(chunk.text)
                            try:
                                stream_callback(chunk.text)
                            except Exception:
                                pass
                        if getattr(chunk, "usage_metadata", None):
                            last_usage = chunk.usage_metadata
                    return "".join(collected), last_usage

                async with safe_timeout(180.0):
                    full_text, usage = await asyncio.to_thread(_run_stream)
            else:
                def _run_once():
                    # 404 NOT_FOUND 回避のため、モデル名に 'models/' プレフィックスが付いていない場合は付与する
                    model_with_prefix = current_model if current_model.startswith('models/') else f'models/{current_model}'
                    return self.client.models.generate_content(
                        model=model_with_prefix,
                        contents=prompt,
                        config=config,
                    )

                async with safe_timeout(120.0):
                    response = await asyncio.to_thread(_run_once)
                full_text = response.text
                usage = getattr(response, "usage_metadata", None)

            story = OutputSanitizer._clean_story(full_text)

            duration = time.time() - start_time
            logger.info(f"✅ Text API Success: model={current_model}, len={len(prompt)}, dur={duration:.2f}s")
            return story, usage

        except Exception as e:
            if not await self._handle_error(e, current_model, retry_state.attempt, retry_state.max_retries):
                raise e
            raise e

    def build_config(self, system_instruction: Optional[str], temp: float, attempt: int, response_schema: Any = None) -> genai_types.GenerateContentConfig:
        return self.build_config_for_mode(system_instruction, temp, attempt, response_schema, "native")

    def build_config_for_mode(self, system_instruction: Optional[str], temp: float, attempt: int, response_schema: Any, mode: str, nsfw_mode: bool = False) -> genai_types.GenerateContentConfig:
        # リトライごとに温度を下げることで、AIの迷走を抑える
        current_temp = max(0.0, temp - (attempt * 0.15))

        config = genai_types.GenerateContentConfig(
            temperature=current_temp,
            system_instruction=system_instruction,
        )

        # NSFWモード時のみセーフティフィルターを緩和
        if nsfw_mode:
            config.safety_settings = [
                genai_types.SafetySetting(
                    category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    threshold="BLOCK_ONLY_HIGH",
                ),
            ]

        if response_schema:
            config.response_mime_type = "application/json"
            if mode == "native":
                config.response_schema = response_schema
            elif mode == "clean_dict":
                schema_dict = get_gemini_schema(response_schema)
                config.response_schema = schema_dict

        return config

    async def _handle_error(self, e: Exception, model_name: str, attempt: int, max_retries: int) -> bool:
        err_msg = str(e).lower()
        if any(x in err_msg for x in ["429", "quota", "503", "unavailable", "500", "502", "internal", "bad gateway"]):
            retry_match = re.search(r'retry\s+in\s+([\d\.]+)', err_msg)
            if retry_match:
                base_wait = float(retry_match.group(1))
            else:
                base_wait = 2.0 ** attempt

            wait_time = min(base_wait, 60.0)
            logger.warning(f"Retrying (Attempt {attempt+1}) after {wait_time:.1f}s due to API congestion.")
            self.cooldown.on_rate_limit()
            await asyncio.sleep(wait_time)
            return True

        if any(x in err_msg for x in ["401", "403", "unauthorized", "invalid key", "api key", "404", "not found", "400", "bad request"]):
            logger.error(f"❌ Unrecoverable Gemini API error: {e}")
            raise LLMUnrecoverableError(f"Unrecoverable Gemini API error: {e}") from e

        return False


class OpenAIApiClient:
    """
    OpenAI互換APIエンドポイントとの通信を担当。
    (vLLM, Ollama, OpenRouter, Together AI等に対応)
    """
    def __init__(self, cooldown: AdaptiveCooldown):
        self.cooldown = cooldown
        self._active_requests = 0

    @with_llm_retry()
    async def generate_json(
        self,
        model_name: str,
        prompt: str,
        system_instruction: Optional[str] = None,
        response_schema: Any = None,
        temp: float = 1.0,
        max_retries: int = 5,
        stream_callback: Optional[Callable[[str], None]] = None,
        retry_state: Optional[RetryState] = None
    ) -> Tuple[Dict[str, Any], str, Any]:
        try:
            import openai
        except ImportError:
            raise ImportError("OpenAI / Gemma integration requires the 'openai' python package. Please install it with 'pip install openai'.")

        from config.project_context import ProjectContext

        base_url = ProjectContext.get_setting("openai_base_url") or "https://api.openai.com/v1"
        api_key = ProjectContext.get_setting("openai_api_key") or "dummy"
        client = openai.AsyncOpenAI(base_url=base_url, api_key=api_key)

        current_temp = retry_state.temp
        current_model = retry_state.model_name
        error_feedback = retry_state.error_feedback

        top_p = ProjectContext.get_setting("inference_top_p", 0.95)
        top_k = ProjectContext.get_setting("inference_top_k", 64)

        system_sandbox = ProjectContext.get_setting("system_sandbox", "")

        system_content = ""
        if system_sandbox:
            system_content += system_sandbox + "\n\n"
        if system_instruction:
            system_content += system_instruction

        messages = []
        if system_content:
            messages.append({"role": "system", "content": system_content})
        messages.append({"role": "user", "content": prompt})

        if error_feedback:
            messages[-1]["content"] = f"【🚨出力形式エラー報告🚨】\n前回の出力に以下の不備がありました: {error_feedback}\n\n{prompt}"

        if response_schema and hasattr(response_schema, "model_fields"):
            fields = list(response_schema.model_fields.keys())
            if "※重要:" not in messages[-1]["content"]:
                messages[-1]["content"] += f"\n\n※重要: JSONには以下のキーを必ず含めてください: {', '.join(fields)}"
                messages[-1]["content"] += "\n\nCRITICAL: Output MUST be valid JSON ONLY. Start with '{' and end with '}'."

        response_format = None
        if response_schema:
            response_format = {"type": "json_object"}

        extra_body = {}
        if top_k:
            extra_body["top_k"] = top_k

        start_time = time.time()
        try:
            from src.core.async_utils import safe_timeout
            async with safe_timeout(120.0):
                response = await client.chat.completions.create(
                    model=current_model,
                    messages=messages,
                    temperature=current_temp,
                    top_p=top_p,
                    response_format=response_format,
                    extra_body=extra_body if extra_body else None,
                )
        except asyncio.TimeoutError as e:
            raise TimeoutError(f"OpenAI API timed out after 120s: {e}")
        except Exception as e:
            err_msg = str(e).lower()
            if any(x in err_msg for x in ["401", "403", "unauthorized", "invalid key", "api key", "404", "not found", "400", "bad request"]):
                logger.error(f"❌ Unrecoverable OpenAI API error: {e}")
                raise LLMUnrecoverableError(f"Unrecoverable OpenAI API error: {e}") from e
            if any(x in err_msg for x in ["429", "quota", "too many requests"]):
                logger.warning(f"⚠️ OpenAI Rate Limit exceeded: {e}")
                from src.core.exceptions import LLMTemporaryError
                raise LLMTemporaryError(f"OpenAI Rate Limit: {e}") from e
            raise e

        full_text = response.choices[0].message.content or ""
        duration = time.time() - start_time

        usage_metadata = response.usage
        prompt_tokens = usage_metadata.prompt_tokens if usage_metadata else 0
        completion_tokens = usage_metadata.completion_tokens if usage_metadata else 0

        class MockUsage:
            def __init__(self, p, c):
                self.prompt_token_count = p
                self.candidates_token_count = c

        usage = MockUsage(prompt_tokens, completion_tokens)

        metadata, story = OutputSanitizer.extract_content_and_metadata(full_text)

        if response_schema and hasattr(response_schema, "model_validate"):
            safe_model_validate(response_schema, metadata)

        self.cooldown.on_success()
        logger.info(f"✅ OpenAI Success: model={current_model}, len={len(prompt)}, dur={duration:.2f}s")
        return metadata, story, usage
