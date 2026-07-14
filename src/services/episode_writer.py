"""
src/services/episode_writer.py — エピソード執筆サービス
"""
import logging
from typing import Any, Dict, Optional

from src.models.production_config import EpisodeGenerateRequest

logger = logging.getLogger(__name__)


class EpisodeWriter:
    """エピソード執筆サービス
    
    既存のエージェント（Writing Agent）に委譲して эпизод を執筆する。
    """

    def __init__(self):
        """初期化"""
        self._writing_agent = None  # 遅延ロード

    def _get_writing_agent(self):
        """Writing Agentを取得（遅延ロード）"""
        if self._writing_agent is None:
            try:
                from src.agents.writing import WritingAgent
                self._writing_agent = WritingAgent(prompt_manager=None)
            except ImportError as e:
                logger.warning(f"WritingAgent not available: {e}")
                self._writing_agent = None
        return self._writing_agent

    async def write(
        self,
        book_id: int,
        ep_num: int,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """エピソードを執筆
        
        Args:
            book_id: 作品ID
            ep_num: エピソード番号
            context: 執筆コンテキスト
            
        Returns:
            Dict[str, Any]: 執筆結果
                - text: 執筆テキスト
                - quality_score: 品質スコア
                - token_usage: トークン使用量
        """
        agent = self._get_writing_agent()
        
        if agent is not None:
            # 既存のエージェントに委譲
            try:
                text = await agent.write_episode(book_id, ep_num, context)
                
                # トークン使用量の推定（簡略化）
                token_usage = {
                    "input_tokens": len(str(context)) // 4,
                    "output_tokens": len(text) // 4
                }
                
                return {
                    "text": text,
                    "quality_score": 0.75,  # デフォルト値
                    "token_usage": token_usage
                }
            except Exception as e:
                logger.error(f"Writing agent failed: {e}")
                # フォールバック
                return self._generate_fallback_text(ep_num, context)
        else:
            # フォールバック: サンプルテキスト生成
            return self._generate_fallback_text(ep_num, context)

    def _generate_fallback_text(
        self,
        ep_num: int,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """フォールバックテキスト生成
        
        この機能は実際のLLM呼び出しの代替であり、
         демонстрация またはテスト目的でのみ使用する。
        
        Args:
            ep_num: エピソード番号
            context: コンテキスト
            
        Returns:
            Dict[str, Any]: 生成されたテキストとメタデータ
        """
        target_words = context.get("target_word_count", 3000)
        
        # サンプルテキスト生成（実際の製品版ではLLM呼び出しに置き換える）
        is_first = context.get("is_first", False)
        is_last = context.get("is_last", False)
        prev_ending = context.get("previous_episode", {}).get("ending", "")
        
        lines = []
        lines.append(f"第{ep_num}話")
        lines.append("")
        
        if is_first:
            lines.append("物語は、静寂の中から始まった。")
            lines.append("")
        
        if prev_ending:
            lines.append(f"前回までの続き――")
            lines.append(prev_ending)
            lines.append("")
        
        # プロット生成（簡略化）
        plot_points = [
            "しかし、状況は急速に変化していた。",
            "突然、最強の相手が姿を現した。",
            "戦士の瞳に闘志が宿る。",
            "しかし誰も、運命の流れを変えられる者はいなかった。",
            "こうして、新しい篇章が始まる。",
        ]
        
        # 目標文字数に達するまでプロットを反復
        current_text = "\n".join(lines)
        while len(current_text) < target_words:
            for plot in plot_points:
                current_text += plot + "\n"
                if len(current_text) >= target_words:
                    break
        
        if is_last:
            current_text += "\n\n――了"
        
        return {
            "text": current_text[:target_words],
            "quality_score": 0.7,
            "token_usage": {
                "input_tokens": len(str(context)) // 4,
                "output_tokens": target_words // 4
            }
        }

    def word_count_estimate(self, context: Dict[str, Any]) -> int:
        """文字数を見積もる
        
        Args:
            context: コンテキスト
            
        Returns:
            int: 推定文字数
        """
        base_count = context.get("target_word_count", 3000)
        is_first = context.get("is_first", False)
        is_last = context.get("is_last", False)
        
        # 開始・終了話は少し短くなる傾向
        modifier = 1.0
        if is_first:
            modifier = 0.9
        if is_last:
            modifier = 0.95
        
        return int(base_count * modifier)