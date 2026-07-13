"""
Context Window Manager - コンテキストウィンドウサイズ管理ユーティリティ

LLMのコンテキストウィンドウサイズを監視し、ウィンドウ使用率が設定値を超えた場合に
警告や自動トリミングを行うサービス。

v4.0: 商用化に向けたコンテキストウィンドウ最適化
"""
import logging
from typing import Any, Dict, Optional

from config import get_config

logger = logging.getLogger(__name__)


class ContextWindowManager:
    """
    コンテキストウィンドウサイズを監視・最適化するマネージャー。
    
    Gemini 3.1 Flash のウィンドウサイズは 1,048,576 tokens。
    目標使用率 (context_window_target_ratio) に基づいて警告や最適化を実施する。
    """

    # 主要モデルのコンテキストウィンドウサイズ (tokens)
    MODEL_CONTEXT_SIZES: Dict[str, int] = {
        "gemma-4-31b-it": 32768,
        "gemini-3.1-flash-lite": 1048576,
        "gemini-3.1-flash": 1048576,
        "gemini-3.0-flash-exp": 1048576,
        "text-embedding-004": 3072,
        "default": 32768,
    }

    # 各パートのデフォルト予約サイズ (tokens)
    DEFAULT_RESERVES: Dict[str, int] = {
        "system_instruction": 2000,
        "response_buffer": 2000,
        "min_reserve": 2000,
    }

    def __init__(self, model_name: Optional[str] = None):
        self.config = get_config()
        self.model_name = model_name or self.config.model_writing
        self.target_ratio = getattr(self.config, 'context_window_target_ratio', 0.85)
        self.min_reserve = getattr(self.config, 'context_window_min_reserve', 2000)

        # コンテキストサイズ取得
        self.max_context = self.MODEL_CONTEXT_SIZES.get(
            self.model_name,
            self.MODEL_CONTEXT_SIZES["default"]
        )

    def estimate_tokens(self, text: str) -> int:
        """
        テキストのトークン数を概算する。
        
        簡易的な估算: 日本語は1文字≈1.5トークン、英語は1単語≈1.3トークン
        より正確な估算が必要な場合は tiktoken 等の使用を推奨。
        """
        if not text:
            return 0

        # 簡易估算: 全文字数を基数として、日本語の比率で補正
        # 実際のプロダクションでは tiktoken や等の使用を推奨
        import re

        # 日本語文字 (ひらがな、カタカナ、漢字)
        japanese_chars = len(re.findall(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]', text))
        # 英数字・記号等
        other_chars = len(text) - japanese_chars

        # 概算トークン数
        estimated = int(japanese_chars * 1.5 + other_chars * 0.5)
        return max(1, estimated)

    def estimate_prompt_tokens(
        self,
        sys_inst: str,
        fw_prompt: str,
        extra_context: Optional[str] = None,
    ) -> int:
        """
        プロンプト全体のトークン数を估算する。
        
        Returns:
            估算トークン数
        """
        total = 0
        total += self.estimate_tokens(sys_inst)
        total += self.estimate_tokens(fw_prompt)
        if extra_context:
            total += self.estimate_tokens(extra_context)
        return total

    def check_window_status(
        self,
        sys_inst: str,
        fw_prompt: str,
        extra_context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        コンテキストウィンドウの使用状況を診断する。
        
        Returns:
            {
                "status": "ok" | "warning" | "critical",
                "estimated_tokens": int,
                "max_context": int,
                "usage_ratio": float,
                "available_tokens": int,
                "recommendations": List[str]
            }
        """
        prompt_tokens = self.estimate_prompt_tokens(sys_inst, fw_prompt, extra_context)
        usage_ratio = prompt_tokens / self.max_context if self.max_context > 0 else 0
        available = self.max_context - prompt_tokens

        recommendations = []
        status = "ok"

        if usage_ratio >= 0.95:
            status = "critical"
            recommendations.append("コンテキスト使用率が95%を超えています。緊急のトリミングが必要です。")
        elif usage_ratio >= self.target_ratio:
            status = "warning"
            recommendations.append(f"コンテキスト使用率が目標値({self.target_ratio:.0%})を超えています。トリミングを推奨します。")

        # レスポンスバッファの警告
        response_buffer_tokens = self.DEFAULT_RESERVES["response_buffer"]
        if available < response_buffer_tokens + 1000:
            recommendations.append(f"レスポンス用バッファが不足しています（残り{available}トークン）。")

        return {
            "status": status,
            "estimated_tokens": prompt_tokens,
            "max_context": self.max_context,
            "usage_ratio": usage_ratio,
            "available_tokens": available,
            "recommendations": recommendations,
        }

    def suggest_trimming(
        self,
        current_tokens: int,
        target_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        トリミングの必要量と方法を提案する。
        
        Args:
            current_tokens: 現在のトークン数
            target_tokens: 目標トークン数（None の場合は target_ratio から算出）
            
        Returns:
            {
                "need_trimming": bool,
                "current_tokens": int,
                "target_tokens": int,
                "tokens_to_remove": int,
                "trim_ratio": float,
                "suggested_sections": List[str]
            }
        """
        if target_tokens is None:
            target_tokens = int(self.max_context * self.target_ratio)

        need_trimming = current_tokens > target_tokens
        tokens_to_remove = max(0, current_tokens - target_tokens)
        trim_ratio = tokens_to_remove / current_tokens if current_tokens > 0 else 0

        suggested_sections = []
        if trim_ratio > 0.3:
            suggested_sections.append("プロンプトテンプレートの一部削減")
            suggested_sections.append("文脈(history)の古いエントリをトリミング")
        if trim_ratio > 0.5:
            suggested_sections.append("ナレーションの詳細を短縮")
            suggested_sections.append("キャラクター描写の重複を削除")

        return {
            "need_trimming": need_trimming,
            "current_tokens": current_tokens,
            "target_tokens": target_tokens,
            "tokens_to_remove": tokens_to_remove,
            "trim_ratio": trim_ratio,
            "suggested_sections": suggested_sections,
        }

    def get_available_for_response(self, sys_inst: str, fw_prompt: str) -> int:
        """
        レスポンス生成に使用できるトークン数を算出する。
        
        Returns:
            利用可能なトークン数
        """
        prompt_tokens = self.estimate_prompt_tokens(sys_inst, fw_prompt)
        reserve = self.min_reserve + self.DEFAULT_RESERVES["response_buffer"]
        available = self.max_context - prompt_tokens - reserve
        return max(0, available)


# グローバルインスタンス
_context_window_manager: Optional[ContextWindowManager] = None

def get_context_window_manager() -> ContextWindowManager:
    """グローバルな ContextWindowManager を取得する"""
    global _context_window_manager
    if _context_window_manager is None:
        _context_window_manager = ContextWindowManager()
    return _context_window_manager
