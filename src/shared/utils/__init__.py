from typing import Any, Dict, Literal, Optional, Protocol

# Constants
COST_INPUT_FLASH  = 0.00000025   # $0.25  / 1M tokens
COST_OUTPUT_FLASH = 0.0000015    # $1.50  / 1M tokens

class StatusReporter(Protocol):
    """UIへのフィードバックを抽象化するインターフェース"""
    def report(self, message: str, level: Literal["info", "warning", "error"] = "info") -> None: ...
    def update_progress(self, current: int, total: int, text: str, sub_text: str = "") -> None: ...

def estimate_tokens(text: str) -> int:
    """Geminiのマルチリンガル・トークナイザーを意識した推定"""
    if not text: return 0
    # 日本語・記号: Gemini 1.5シリーズは約0.6〜0.8トークン/文字。0.7で計算。
    ja_chars = len(__import__("re").findall(r'[^\x00-\x7F]', text))
    # 英数字: 約1.3トークン/単語
    en_words = len(__import__("re").findall(r'\w+', text))
    return int(ja_chars * 0.7 + en_words * 1.3)

class TokenUsageTracker:
    def __init__(self, stats_dict: dict):
        self.stats = stats_dict

    def add_usage(self, prompt_tokens: int, completion_tokens: int) -> None:
        self.stats["prompt"]     += prompt_tokens
        self.stats["completion"] += completion_tokens
        self.stats["calls"]      += 1

    def get_cost_usd(self) -> float:
        return (self.stats["prompt"] * COST_INPUT_FLASH) + (self.stats["completion"] * COST_OUTPUT_FLASH)

    def get_summary(self) -> str:
        return (
            f"API呼び出し: {self.stats['calls']}回 | "
            f"推定コスト: ${self.get_cost_usd():.4f}"
        )

    def display_cost_estimate(self, text: str, label: str = "内容") -> None:
        """Streamlit上にトークン数と推定コストをキャプション表示する"""
        try:
            import streamlit as st
            tokens = estimate_tokens(text)
            avg_rate = (COST_INPUT_FLASH + COST_OUTPUT_FLASH) / 2
            cost   = tokens * avg_rate
            st.caption(f"{label} 推定トークン: {tokens} (概算コスト: ${cost:.6f})")
        except Exception:
            pass
