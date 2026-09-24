"""
局所パッチ（Single-shot Polish） - 指摘された特定シーンのみの再生成
"""

from typing import Tuple
from src.audit.unified_llm_auditor import call_llm_api


class LocalPolisher:
    """局所パッチを実行するクラス - 特定範囲のみのテキスト再生成"""
    
    def polish(self, text: str, target_range: Tuple[int, int], improvement_instruction: str) -> str:
        """
        指定された範囲のテキストのみを改善（局所パッチ）
        
        Args:
            text: 元のテキスト
            target_range: (start_index, end_index) - 改善対象の範囲（end_indexは排他的）
            improvement_instruction: 改善のための指示（例: "より感情豊かに書き直して"）
            
        Returns:
            str: 局所パッチ適用後のテキスト
        """
        start_idx, end_idx = target_range
        
        # 範囲の妥当性をチェック
        if start_idx < 0 or end_idx > len(text) or start_idx >= end_idx:
            # 範囲が無効な場合は元のテキストを返す
            return text
        
        # 対象範囲のテキストを抽出
        target_text = text[start_idx:end_idx]
        
        # 前後の文脈を取得（プロンプトに含めるため）
        # 前方文脈：対象範囲の開始位置から前の50文字か、文頭まで
        context_start = max(0, start_idx - 50)
        before_context = text[context_start:start_idx]
        
        # 後方文脈：対象範囲の終了位置から後の50文字か、文末まで
        context_end = min(len(text), end_idx + 50)
        after_context = text[end_idx:context_end]
        
        # プロンプトを構築
        prompt = self._create_polish_prompt(
            before_context, target_text, after_context, improvement_instruction
        )
        
        try:
            # LLMを呼び出して改善されたテキストを生成
            improved_text = call_llm_api(prompt)
            
            # 生成されたテキストを元のテキストに組み込む
            # 前半 + 改善テキスト + 後半
            polished_text = text[:start_idx] + improved_text.strip() + text[end_idx:]
            
            return polished_text
        except Exception:
            # LLM呼び出しに失敗した場合は元のテキストを返す
            # フォールバック機構はStep 18で実装予定
            return text
    
    def _create_polish_prompt(self, before_context: str, target_text: str, 
                            after_context: str, improvement_instruction: str) -> str:
        """
        局所パッチ用のプロンプトを構築
        """
        prompt = f"""
あなたは小説の執筆を補助する専門編集アシスタントです。
以下の文脈を考慮して、指定された範囲のテキストを改善してください。

前方文脈：
{before_context}

対象範囲：
{target_text}

後方文脈：
{after_context}

改善指示：
{improvement_instruction}

上記の文脈と改善指示を考慮して、対象範囲のテキストを改善してください。
改善後のテキストのみを返してください（前方文脈と後方文脈は含めないでください）。
"""
        return prompt.strip()