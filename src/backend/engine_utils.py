import asyncio
import math
import re
from typing import Any, List

from config import STYLE_DEFINITIONS

try:
    from pydantic.errors import PydanticUserError
except ImportError:
    PydanticUserError = Exception

from src.core.exceptions import LLMValidationError
from src.core.observability import StructuredLogger
from src.core.rate_limiter import TokenBucket

logger = StructuredLogger(__name__)


def compute_ngram_similarity(text1: str, text2: str, n: int = 2) -> float:
    """
    bi-gram Jaccard類似度による高速類似度計算。
    embedding不要。0.0-1.0 を返す。
    日本語・英語混合テキスト対応のため、トークンベースのn-gramを採用。
    """
    if not text1 or not text2:
        return 0.0

    def get_token_ngrams(s: str, n: int):
        tokens = s.split()
        if not tokens:
            return set()
        ngrams = set()
        for token in tokens:
            token_lower = token.lower()
            if len(token_lower) >= n:
                ngrams.update(token_lower[i : i + n] for i in range(len(token_lower) - n + 1))
        return ngrams

    grams1 = get_token_ngrams(text1, n)
    grams2 = get_token_ngrams(text2, n)

    if not grams1 or not grams2:
        return 0.0

    intersection = len(grams1 & grams2)
    union = len(grams1 | grams2)

    return intersection / union if union > 0 else 0.0


def compute_cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    2つのベクトル間のコサイン類似度を計算する。
    0.0-1.0 を返す。
    """
    if not vec1 or not vec2:
        return 0.0
    if len(vec1) != len(vec2):
        return 0.0

    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(v * v for v in vec1))
    norm2 = math.sqrt(sum(v * v for v in vec2))

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return dot / (norm1 * norm2)


def is_light_style(style_key: str, genre: str) -> bool:
    """スタイルまたはジャンルから、コミカル/ライトな作風かを一元判定する"""
    style_cfg = STYLE_DEFINITIONS.get(style_key, {})
    if style_cfg.get("is_light"):
        return True

    # ジャンルキーワードによる判定
    light_keywords = ["ほのぼの", "スローライフ", "コメディ", "ギャル", "配信", "飯テロ"]
    if any(k in genre for k in light_keywords):
        return True
    return False


def safe_model_validate(model_cls: Any, data: Any) -> Any:
    """
    Pydanticモデルのバリデーションを安全に実行する。
    定義未完了エラーが発生した場合、自動で model_rebuild を実行してリトライする。
    """
    try:
        return model_cls.model_validate(data)
    except PydanticUserError as e:
        if "not fully defined" in str(e) or "class_not_fully_defined" in str(e):
            logger.info(f"🔄 自動修復: モデル {model_cls.__name__} を再構築してリトライします。")
            model_cls.model_rebuild()
            return model_cls.model_validate(data)
        logger.error(f"Model validation failed for {model_cls.__name__}: {e}", exc_info=True)
        raise LLMValidationError(f"Model validation failed: {e}") from e


def verify_character_tone(original_text: str, corrected_text: str) -> List[str]:
    """リズム補正前後で台詞の口調が変わっていないか検証する。"""
    errors: List[str] = []
    dialogues_orig = re.findall(r"「(.*?)」", original_text, re.DOTALL)
    dialogues_corr = re.findall(r"「(.*?)」", corrected_text, re.DOTALL)

    if abs(len(dialogues_orig) - len(dialogues_corr)) > 1:
        errors.append("口調警告: 台詞の総数が大幅に変化しています。")
        return errors

    try:
        from sudachipy import dictionary as sudachi_dict
        from sudachipy import tokenizer as sudachi_tokenizer

        tokenizer_obj = sudachi_dict.Dictionary().create()
        mode = sudachi_tokenizer.Tokenizer.SplitMode.C

        for i, (orig, corr) in enumerate(zip(dialogues_orig, dialogues_corr)):
            if orig == corr:
                continue

            def _get_end(txt):
                tokens = [
                    t
                    for t in tokenizer_obj.tokenize(txt.strip(), mode)
                    if t.part_of_speech()[0] not in ["補助記号"]
                ]
                return tokens[-1] if tokens else None

            orig_end, corr_end = _get_end(orig), _get_end(corr)
            if not orig_end or not corr_end:
                continue
            if orig_end.part_of_speech()[0] in ["助動詞", "助詞"]:
                if orig_end.surface() != corr_end.surface():
                    errors.append(
                        f"口調警告: 第{i + 1}番目の台詞文末が変化: 「{orig_end.surface()}」→「{corr_end.surface()}」"
                    )
    except ImportError:
        logger.info("sudachipy not available, using regex fallback for tone verification")
        for i, (orig, corr) in enumerate(zip(dialogues_orig, dialogues_corr)):
            if orig == corr:
                continue
            orig_end = re.sub(r"[？！。、]", "", orig.strip())[-2:]
            corr_end = re.sub(r"[？！。、]", "", corr.strip())[-2:]
            if orig_end != corr_end:
                errors.append(
                    f"口調警告: 第{i + 1}番目の台詞文末が変化: 「{orig_end}」→「{corr_end}」"
                )
    return errors


def safe_run_async(coro):
    """同期コンテキストから非同期コルーチンを実行する。

    既にイベントループが動作中の場合（Streamlit/FastAPI）、
    既存ループへコルーチンをスケジュールする。
    """
    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
            # 既存ループへスケジュール（スレッドプール生成コスト回避）
            future = asyncio.run_coroutine_threadsafe(coro, loop)
            return future.result()

        # ループはあるが動いていない（稀なケース）
        return asyncio.run(coro)
    except RuntimeError:
        # ループが動いていない場合は asyncio.run が安全
        return asyncio.run(coro)


class AdaptiveCooldown:
    """
    TokenBucketをラップし、APIの負荷状況に応じて補充レートを動的に調整する。
    旧来の wait/on_success 等のインターフェースを維持しつつ、内部的にTokenBucketで流量制御を行う。
    """

    def __init__(
        self, base_sec: float, min_sec: float, max_sec: float, name: str = "adaptive_cooldown"
    ):
        # base_sec を 1秒あたりのリクエスト数(fill_rate)に変換
        # 例: base_sec=2.0s -> fill_rate=0.5 req/s
        initial_fill_rate = 1.0 / max(0.1, base_sec)
        self.bucket = TokenBucket(
            capacity=1.0,  # バーストを抑えるため基本1
            fill_rate=initial_fill_rate,
            name=name,
        )
        self.min_rate = 1.0 / max(0.1, max_sec)
        self.max_rate = 1.0 / max(0.01, min_sec)
        self._consecutive_successes = 0

    async def wait(self):
        """トークンが補充されるまで待機する"""
        await self.bucket.wait_and_consume(1.0)

    async def _fire_adjust_rate(self, factor: float):
        """レート調整を非同期で実行し、例外はログに記録する。"""
        try:
            await self.bucket.adjust_rate(factor)
        except Exception as e:
            logger.warning(f"Failed to adjust rate (factor={factor}): {e}")

    def on_success(self):
        """成功時に補充レートを徐々に上げる"""
        self._consecutive_successes += 1
        if self._consecutive_successes >= 5:
            asyncio.create_task(self._fire_adjust_rate(1.1))
            if self.bucket.fill_rate > self.max_rate:
                self.bucket.fill_rate = self.max_rate
            self._consecutive_successes = 0

    def on_rate_limit(self):
        """429/503エラー時に補充レートを大幅に下げる"""
        asyncio.create_task(self._fire_adjust_rate(0.4))
        if self.bucket.fill_rate < self.min_rate:
            self.bucket.fill_rate = self.min_rate

    def on_error(self):
        """一般エラー時に補充レートを少し下げる"""
        asyncio.create_task(self._fire_adjust_rate(0.8))
        if self.bucket.fill_rate < self.min_rate:
            self.bucket.fill_rate = self.min_rate


def safe_get(data: Any, key: str, default: Any = None) -> Any:
    """辞書またはオブジェクトから安全に値を取得する"""
    if data is None:
        return default
    if isinstance(data, dict):
        return data.get(key, default)
    return getattr(data, key, default)


def extract_markdown_content(text: str) -> str:
    """Extracts content from a markdown code block if present.

     다양한言語指定子 (例: ```python, ```js) を持つフェンスブロック霞対応。
    最初のフェンスブロックの内容を抽出します。
    """
    if not text:
        return ""

    fence_pattern = re.compile(r"^```(\w*)\s*\n", re.MULTILINE)
    match = fence_pattern.search(text)
    if not match:
        return text.strip()

    match.group(1)
    start = match.end()
    end_fence = text.find("```", start)
    if end_fence == -1:
        return text[start:].strip()
    return text[start:end_fence].strip()
