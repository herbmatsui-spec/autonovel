import asyncio
import inspect
import logging
from functools import wraps
from typing import Any, Dict

from pydantic import ValidationError

from src.core.exceptions import (
    LLMTemporaryError,
    LLMTokenLimitError,
    LLMUnrecoverableError,
    LLMValidationError,
)

logger = logging.getLogger(__name__)

class RetryState:
    """LLM呼び出しの試行状態を追跡・管理するクラス"""
    def __init__(self, max_retries: int, temp: float, model_name: str, reporter: Any = None):
        self.max_retries = max_retries
        self.attempt = 0
        self.temp = temp
        self.model_name = model_name
        self.original_model_name = model_name
        self.reporter = reporter
        self.error_feedback = ""
        self.consecutive_5xx = 0

def _extract_llm_params(func, args, kwargs) -> Dict[str, Any]:
    """引数から max_retries, temp, model_name, reporter を動的に抽出する"""
    # 1. 第一引数（selfの次）が LLMRequestOptions オブジェクトの場合
    if len(args) > 1 and hasattr(args[1], "model_name") and hasattr(args[1], "prompt"):
        req = args[1]
        return {
            "max_retries": getattr(req, "max_retries", 5),
            "temp": getattr(req, "temp", 0.7),
            "model_name": getattr(req, "model_name", ""),
            "reporter": getattr(req, "reporter", None),
        }

    # kwargsに直接requestオブジェクトがある場合
    if "request" in kwargs and hasattr(kwargs["request"], "model_name"):
        req = kwargs["request"]
        return {
            "max_retries": getattr(req, "max_retries", 5),
            "temp": getattr(req, "temp", 0.7),
            "model_name": getattr(req, "model_name", ""),
            "reporter": getattr(req, "reporter", None),
        }

    # 2. シグネチャから引数名を解決する
    sig = inspect.signature(func)
    try:
        bound = sig.bind_partial(*args, **kwargs)
        bound.apply_defaults()
        resolved_kwargs = bound.arguments
    except Exception:
        resolved_kwargs = kwargs

    # selfを除外した引数マップ
    func_args = {k: v for k, v in resolved_kwargs.items() if k != "self"}

    if "request" in func_args and hasattr(func_args["request"], "model_name"):
        req = func_args["request"]
        return {
            "max_retries": getattr(req, "max_retries", 5),
            "temp": getattr(req, "temp", 0.7),
            "model_name": getattr(req, "model_name", ""),
            "reporter": getattr(req, "reporter", None),
        }

    return {
        "max_retries": func_args.get("max_retries", 5),
        "temp": func_args.get("temp", 0.7),
        "model_name": func_args.get("model_name", ""),
        "reporter": func_args.get("reporter", None),
    }

def with_llm_retry():
    """LLM呼び出しのリトライ処理を共通化するカスタムデコレータ"""
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            params = _extract_llm_params(func, (self,) + args, kwargs)

            # 引数に retry_state が明示的に渡されていない場合は新規生成
            state = kwargs.get("retry_state")
            if not state:
                state = RetryState(
                    max_retries=params["max_retries"],
                    temp=params["temp"],
                    model_name=params["model_name"],
                    reporter=params["reporter"]
                )
                kwargs["retry_state"] = state

            while state.attempt < state.max_retries:
                # UI通知 (2回目以降の試行時)
                if state.attempt > 0 and state.reporter and hasattr(state.reporter, "report"):
                    state.reporter.report(
                        f"🔄 JSON生成再試行中 ({state.attempt + 1}/{state.max_retries}) | モデル: {state.model_name}",
                        "warning"
                    )

                # cooldown待機
                if hasattr(self, "cooldown") and self.cooldown:
                    await self.cooldown.wait()

                # 並行リクエスト数のインクリメント
                if hasattr(self, "_lock"):
                    with self._lock:
                        if hasattr(self, "_active_requests"):
                            self._active_requests += 1
                else:
                    if hasattr(self, "_active_requests"):
                        self._active_requests += 1

                try:
                    # メソッド実行
                    result = await func(self, *args, **kwargs)

                    # 成功時の後処理
                    if hasattr(self, "cooldown") and self.cooldown:
                        self.cooldown.on_success()
                    if hasattr(self, "_lock") and hasattr(self, "_consecutive_5xx"):
                        with self._lock:
                            self._consecutive_5xx = 0
                    elif hasattr(self, "_consecutive_5xx"):
                        self._consecutive_5xx = 0

                    return result

                except ValidationError as ve:
                    # Pydanticのバリデーションエラー
                    from src.backend.sanitizer import OutputSanitizer
                    state.error_feedback = OutputSanitizer.format_validation_error(ve)
                    logger.warning(f"Validation failed (Attempt {state.attempt + 1}): {state.error_feedback}")
                    if state.attempt == state.max_retries - 1:
                        raise LLMValidationError(f"Validation failed after {state.max_retries} attempts: {state.error_feedback}") from ve
                    # 適応的温度調整: バリデーションエラー時は温度を下げる
                    state.temp = max(0.0, state.temp - 0.1)
                    if state.reporter and hasattr(state.reporter, "report"):
                        state.reporter.report(
                            f"🔄 出力形式エラーを検知。精度を高めるため温度を下げて再試行します (Temp: {state.temp:.1f})",
                            "warning"
                        )

                except (LLMUnrecoverableError, LLMTokenLimitError, LLMValidationError) as e:
                    # すでに定義済みの致命的エラーはリトライせず即座に伝播
                    logger.error(f"❌ Fatal LLM error detected. Fail-Fast. Error: {e}")
                    raise e
                except Exception as e:
                    # コードのバグやプログラム論理エラーはFail-Fastで即座に投げる
                    if isinstance(e, (TypeError, NameError, AttributeError, KeyError)):
                        raise e

                    err_msg = str(e).lower() or repr(e).lower()

                    # 1. トークン超過の判定（Fail-Fast対象）
                    if any(x in err_msg for x in ["token limit", "context window", "too many tokens", "resource exhausted"]):
                        logger.error(f"❌ Token limit exceeded. Fail-Fast. Error: {e}")
                        raise LLMTokenLimitError(f"Token limit exceeded: {e}") from e

                    # モデル名未指定の判定を追加
                    if "model is required" in err_msg:
                        logger.error(f"❌ AIモデル名が空の状態でAPIが呼ばれました。UIの詳細設定でモデル名が空欄になっていないか確認してください。 Error: {e}")
                        raise LLMUnrecoverableError(f"Model name is empty: {e}") from e

                    # 2. 復旧不可能なエラーの判定（Fail-Fast対象）
                    if any(x in err_msg for x in ["404", "not found", "unauthorized", "invalid key", "api key", "unauthenticated"]):
                        logger.error(f"❌ Fatal unrecoverable LLM error. Fail-Fast. Error: {e}")
                        raise LLMUnrecoverableError(f"Fatal unrecoverable LLM error: {e}") from e

                    # 3. 一時的なエラーの判定
                    is_timeout = isinstance(e, asyncio.TimeoutError) or "timeout" in err_msg or "deadline" in err_msg
                    is_retryable = any(
                        x in err_msg
                        for x in ["429", "quota", "503", "unavailable", "500", "502", "internal", "bad gateway"]
                    ) or is_timeout

                    if not is_retryable:
                        logger.error(f"❌ Non-retryable error. Fail-Fast. Error: {e}")
                        raise LLMUnrecoverableError(f"Non-retryable error: {e}") from e

                    if state.attempt == state.max_retries - 1:
                        logger.error(f"❌ Max retries reached for temporary error: {e}")
                        raise LLMTemporaryError(f"Temporary LLM error persisted after {state.max_retries} attempts: {e}") from e

                    # 動的クールダウンと並行抑制
                    if hasattr(self, "cooldown") and self.cooldown:
                        if any(x in err_msg for x in ["429", "quota", "503"]):
                            self.cooldown.on_rate_limit()
                        else:
                            self.cooldown.on_error()

                    # 待機時間の計算とスリープ (指数バックオフ)
                    # 適応的バックオフ戦略
                    # 429 (Too Many Requests) の場合はより強力な指数バックオフを適用
                    if "429" in err_msg or "quota" in err_msg:
                        wait_time = min(2.0 * (2 ** state.attempt), 60.0)
                    # 5xx系サーバーエラーの場合は中程度のバックオフ
                    elif any(x in err_msg for x in ["503", "500", "unavailable"]):
                        wait_time = min(3.0 * (2 ** state.attempt), 20.0)
                    # その他の一時的エラー
                    else:
                        wait_time = min(1.0 * (2 ** state.attempt), 10.0)

                    # UIへの警告表示
                    if state.reporter and hasattr(state.reporter, "report"):
                        state.reporter.report(
                            f"🔄 API一時エラーを検知 (試行 {state.attempt + 1})。{wait_time:.1f}秒後にリトライします...",
                            "warning"
                        )

                    # 5xx 連続エラーのカウントアップとモデルフォールバック
                    if is_timeout or any(x in err_msg for x in ["503", "500", "deadline", "exhausted"]):
                        if hasattr(self, "_lock") and hasattr(self, "_consecutive_5xx"):
                            with self._lock:
                                self._consecutive_5xx += 1
                                fail_count = self._consecutive_5xx
                        elif hasattr(self, "_consecutive_5xx"):
                            self._consecutive_5xx += 1
                            fail_count = self._consecutive_5xx
                        else:
                            fail_count = 1

                        if fail_count >= 2:
                            from config import MODEL_STABLE_FALLBACK
                            try:
                                from config import MODEL_ULTRA_STABLE
                            except ImportError:
                                MODEL_ULTRA_STABLE = MODEL_STABLE_FALLBACK

                            if state.model_name != MODEL_ULTRA_STABLE and (state.attempt >= 2 or state.model_name == MODEL_STABLE_FALLBACK):
                                state.model_name = MODEL_ULTRA_STABLE if MODEL_ULTRA_STABLE else "gemini-2.0-flash"
                                logger.warning(f"[Gemini FALLBACK] Persistent 5xx. Switching to ULTRA_STABLE: {state.model_name}")
                            elif state.model_name != MODEL_STABLE_FALLBACK and MODEL_STABLE_FALLBACK != state.original_model_name:
                                state.model_name = MODEL_STABLE_FALLBACK if MODEL_STABLE_FALLBACK else "gemini-2.0-flash"
                                logger.warning(f"[Gemini FALLBACK] 5xx detected. Switching to STABLE_FALLBACK: {state.model_name}")

                    await asyncio.sleep(wait_time)

                finally:
                    # 並行リクエスト数のデクリメント
                    if hasattr(self, "_lock"):
                        with self._lock:
                            if hasattr(self, "_active_requests"):
                                self._active_requests -= 1
                                if self._active_requests < 0:
                                    self._active_requests = 0
                    else:
                        if hasattr(self, "_active_requests"):
                            self._active_requests -= 1
                            if self._active_requests < 0:
                                self._active_requests = 0

                state.attempt += 1

            raise LLMTemporaryError("Max retries exceeded")
        return wrapper
    return decorator
