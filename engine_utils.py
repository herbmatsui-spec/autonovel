import re
import asyncio
import logging
import time
from typing import List, Any
from config import STYLE_DEFINITIONS

try:
    from pydantic.errors import PydanticUserError
except ImportError:
    PydanticUserError = Exception

logger = logging.getLogger(__name__)

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
    except (PydanticUserError, Exception) as e:
        if "not fully defined" in str(e) or "class_not_fully_defined" in str(e):
            logger.info(f"🔄 自動修復: モデル {model_cls.__name__} を再構築してリトライします。")
            model_cls.model_rebuild()
            return model_cls.model_validate(data)
        raise

def verify_character_tone(original_text: str, corrected_text: str) -> List[str]:
    """リズム補正前後で台詞の口調が変わっていないか検証する。"""
    errors: List[str] = []
    dialogues_orig = re.findall(r'「(.*?)」', original_text, re.DOTALL)
    dialogues_corr = re.findall(r'「(.*?)」', corrected_text, re.DOTALL)

    if abs(len(dialogues_orig) - len(dialogues_corr)) > 1:
        errors.append(f"口調警告: 台詞の総数が大幅に変化しています。")
        return errors

    try:
        from sudachipy import dictionary as sudachi_dict, tokenizer as sudachi_tokenizer
        tokenizer_obj = sudachi_dict.Dictionary().create()
        mode = sudachi_tokenizer.Tokenizer.SplitMode.C

        for i, (orig, corr) in enumerate(zip(dialogues_orig, dialogues_corr)):
            if orig == corr: continue
            def _get_end(txt):
                tokens = [t for t in tokenizer_obj.tokenize(txt.strip(), mode) if t.part_of_speech()[0] not in ["補助記号"]]
                return tokens[-1] if tokens else None
            orig_end, corr_end = _get_end(orig), _get_end(corr)
            if not orig_end or not corr_end: continue
            if orig_end.part_of_speech()[0] in ["助動詞", "助詞"]:
                if orig_end.surface() != corr_end.surface():
                    errors.append(f"口調警告: 第{i+1}番目の台詞文末が変化: 「{orig_end.surface()}」→「{corr_end.surface()}」")
    except ImportError:
        for i, (orig, corr) in enumerate(zip(dialogues_orig, dialogues_corr)):
            if orig == corr: continue
            orig_end = re.sub(r'[？！。、]','', orig.strip())[-2:]
            corr_end = re.sub(r'[？！。、]','', corr.strip())[-2:]
            if orig_end != corr_end:
                errors.append(f"口調警告: 第{i+1}番目の台詞文末が変化: 「{orig_end}」→「{corr_end}」")
    return errors

def safe_run_async(coro):
    """Streamlitのイベントループ内で非同期処理を安全に実行する"""
    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
            import concurrent.futures
            def _worker(c):
                new_loop = asyncio.new_event_loop()
                try:
                    asyncio.set_event_loop(new_loop)
                    return new_loop.run_until_complete(c)
                finally:
                    new_loop.close()

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                return executor.submit(_worker, coro).result()

        # ループはあるが動いていない（稀なケース）
        return asyncio.run(coro)
    except RuntimeError:
        # ループが動いていない場合は asyncio.run が安全
        return asyncio.run(coro)

class AdaptiveCooldown:
    """APIの負荷状況に応じて待機時間を動的に調整する"""
    def __init__(self, base_sec: float, min_sec: float, max_sec: float):
        self.base_sec = base_sec # Ensure this line and subsequent lines are correctly indented (e.g., 8 spaces from column 0)
        self.min_sec = min_sec
        self.max_sec = max_sec
        self._current = base_sec
        self._consecutive_successes = 0

    async def wait(self):
        await asyncio.sleep(max(self.min_sec, min(self._current, self.max_sec)))

    def on_success(self):
        self._consecutive_successes += 1
        if self._consecutive_successes >= 5:
            # 5回連続成功して初めて、待機時間を10%ずつ慎重に短縮する
            self._current = max(self.min_sec, self._current * 0.9)
            self._consecutive_successes = 0

    def on_rate_limit(self):
        self._current = min(self.max_sec, self._current * 2.5) # 503/429時はより厳しくクールダウンを延長

    def on_error(self):
        self._current = min(self.max_sec, self._current * 1.5)