import asyncio
import threading

from src.core.observability import get_structured_logger

logger = get_structured_logger("llm_client")
from typing import Any, Callable, Optional

from src.core.llm_gateway import GeminiApiClient
from src.models import GenerateResult


class EngineLLMClient:
    def __init__(self, ai_api: GeminiApiClient):
        self.ai_api = ai_api
        self._local = threading.local()

    def _safe_update_token_stats(self, prompt: int, completion: int, reporter: Any = None) -> None:
        try:
            if reporter and hasattr(reporter, "state"):
                reporter.state.token_usage["prompt"] += prompt
                reporter.state.token_usage["completion"] += completion
                reporter.state.token_usage["calls"] += 1
        except (AttributeError, RuntimeError, KeyError):
            logger.debug("Token stats update skipped", prompt=prompt, completion=completion)

    async def generate_json(
        self,
        model_name: str,
        prompt: str,
        response_schema: Any = None,
        system_instruction: Optional[str] = None,
        temp: float = 0.7,
        expected_ep_num: Optional[int] = None,
        stream_callback: Optional[Callable[[str], None]] = None,
    ) -> GenerateResult:
        try:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                return GenerateResult(success=False, error_type="LOOP_ERROR", error_message="No running event loop")

            if not hasattr(self._local, "sems"):
                self._local.sems = {}

            if loop not in self._local.sems or loop.is_closed():
                max_conc = 8
                self._local.sems[loop] = asyncio.Semaphore(max_conc)

            async with self._local.sems[loop]:
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

    async def generate_text(self, *args, **kwargs):
        return await self.generate_json(*args, **kwargs)

