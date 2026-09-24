"""
Unified LLM auditor that evaluates multiple aspects in a single LLM call.
Consolidates 8 specialist auditors into one LLM call for cost and latency reduction.
"""

from typing import List, Optional, Tuple
import json
from dataclasses import dataclass


@dataclass
class Issue:
    """Represents an issue found by the auditor."""
    type: str  # Issue category (e.g., "plot_inconsistency", "character_appeal")
    message: str  # Human-readable description
    location: Optional[Tuple[int, int]] = None  # (start_index, end_index) or None if location unknown
    suggestion: Optional[str] = None  # Optional suggestion for fixing the issue


# Module-level function that can be easily mocked in tests
def call_llm_api(prompt: str, system_prompt: Optional[str] = None) -> str:
    """
    LLM APIを呼び出す関数。
    実際の実装では、ここでLLMクライアントを使ってAPIコールを行う。
    テストではこの関数をモックする。
    
    Args:
        prompt: ユーザープロンプト
        system_prompt: システムプロンプト（オプション）
        
    Returns:
        str: LLMからの生のレスポンス（文字列）
    """
    # This is a placeholder - in real implementation, this would call an actual LLM
    # For now, we'll raise NotImplementedError to indicate this needs to be implemented
    # or return a default value for testing purposes when not mocked
    raise NotImplementedError("LLM API呼び出しが実装されていません")


class UnifiedLLMAuditor:
    """統合LLMオーディター - 1回のLLMコールで複数観点を評価"""
    
    def __init__(self):
        """Unified LLM Auditorを初期化"""
        # 現状では特に初期化するものはない
        # LLMクライアントはcall_llm_api関数を通じてアクセス
        pass
        
    def audit(self, text: str) -> List[Issue]:
        """
        テキストに対して統合LLMオーディットを実行
        
        Args:
            text: 評価対象のテキスト
            
        Returns:
            List[Issue]: 検出された問題のリスト
        """
        # 監査用プロンプトを構築
        prompt = self._construct_audit_prompt(text)
        
        try:
            # LLM APIを呼び出し
            response = call_llm_api(prompt)
            
            # レスポンスをパースしてIssueオブジェクトのリストを返す
            return self._parse_llm_response(response)
        except Exception:
            # エラーが発生した場合は空のリストを返す（フォールバックはStep 18で実装）
            return []
        
    def _construct_audit_prompt(self, text: str) -> str:
        """
        統合監査用のプロンプトを構築
        8つの観点（プロットの一貫性、キャラクターの魅力など）を評価するようLLMに指示
        """
        prompt = f"""
あなたは小説の品質を多角的に評価する専門編集オーディターです。
以下のテキストについて、8つの観点で評価し、問題がある場合は指摘してください：

1. プロットの一貫性
2. キャラクターの魅力  
3. 文体の適切さ
4. 感情の起伏
5. オリジナリティ
6. ジャンル適合性
7. 読みやすさ
8. 総合エンターテインメント性

評価対象テキスト：
{text}

以下のJSON形式で結果を返してください：
[
  {{"type": "issue_type", "message": "issue description"}},
  ...
]

issue_typeには以下のいずれかを使用してください：
- plot_inconsistency
- character_appeal  
- style_appropriateness
- emotional_variety
- originality
- genre_fit
- readability
- overall_entertainment

問題がない場合は空の配列 [] を返してください。
"""
        return prompt.strip()
        
    def _parse_llm_response(self, response: str) -> List[Issue]:
        """
        LLMからの生のレスポンスをIssueオブジェクトのリストにパース
        """
        issues = []
        
        try:
            # JSONをパース
            data = json.loads(response.strip())
            
            # 配列であることを確認
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and "type" in item and "message" in item:
                        issues.append(Issue(
                            type=item["type"],
                            message=item["message"]
                        ))
        except (json.JSONDecodeError, AttributeError, KeyError):
            # パースに失敗した場合は空のリストを返す
            pass
            
        return issues