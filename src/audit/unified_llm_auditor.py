"""
Unified LLM auditor that evaluates multiple aspects in a single LLM call.
Consolidates 8 specialist auditors into one LLM call for cost and latency reduction.
"""

import asyncio
import json
import logging
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


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
    テストではこの関数をモックする。未モック時は実アダプタ連携を試みる。
    
    Args:
        prompt: ユーザープロンプト
        system_prompt: システムプロンプト（オプション）
        
    Returns:
        str: LLMからの生のレスポンス（文字列）
    """
    try:
        from src.services.llm.factory import get_llm_adapter
        adapter = get_llm_adapter()
        if hasattr(adapter, "generate_text_sync"):
            return adapter.generate_text_sync(prompt=prompt, system_prompt=system_prompt)
        elif hasattr(adapter, "generate_text"):
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            if loop and loop.is_running():
                # 既にイベントループが動いている場合はブロッキング回避のためスレッドで実行
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, adapter.generate_text(prompt=prompt, system_prompt=system_prompt))
                    return future.result(timeout=30)
            else:
                return asyncio.run(adapter.generate_text(prompt=prompt, system_prompt=system_prompt))
    except Exception as e:
        logger.warning("Default LLM adapter call failed: %s", e)
        raise NotImplementedError("LLM API呼び出しが実装されていないか利用できません") from e
    raise NotImplementedError("LLM API呼び出しが実装されていません")


class UnifiedLLMAuditor:
    """統合LLMオーディター - 1回のLLMコールで複数観点を評価"""
    
    def __init__(self):
        """Unified LLM Auditorを初期化"""
        pass
        
    def audit(self, text: str) -> List[Issue]:
        """
        テキストに対して統合LLMオーディットを実行
        
        Args:
            text: 評価対象のテキスト
            
        Returns:
            List[Issue]: 検出された問題のリスト
        """
        if not text:
            return []

        # 監査用プロンプトを構築
        prompt = self._construct_audit_prompt(text)
        
        try:
            # LLM APIを呼び出し
            response = call_llm_api(prompt)
            
            # レスポンスをパースしてIssueオブジェクトのリストを返す
            return self._parse_llm_response(response)
        except Exception as e:
            logger.debug("UnifiedLLMAuditor error: %s", e)
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

以下のJSON形式で結果を返してください（コードブロック等を使わずJSON配列のみを出力してください）：
[
  {{"type": "issue_type", "message": "issue description", "suggestion": "optional suggestion"}}
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
        
    def _extract_json_string(self, response: str) -> str:
        """Markdownコードブロックや前後の説明文からJSON文字列を抽出"""
        if not response:
            return "[]"
        # 1. ```json ... ``` または ``` ... ``` を抽出
        code_block = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", response, re.IGNORECASE)
        if code_block:
            return code_block.group(1).strip()
        
        # 2. [ ... ] 配列を抽出
        array_match = re.search(r"\[\s*\{[\s\S]*\}\s*\]", response)
        if array_match:
            return array_match.group(0).strip()

        # 3. 空配列 []
        if "[]" in response:
            return "[]"

        return response.strip()

    def _parse_llm_response(self, response: str) -> List[Issue]:
        """
        LLMからの生のレスポンスをIssueオブジェクトのリストにパース
        """
        issues = []
        if not response:
            return issues
        
        try:
            cleaned_json = self._extract_json_string(response)
            data = json.loads(cleaned_json)
            
            # 配列であることを確認
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and "type" in item and "message" in item:
                        loc = None
                        if "location" in item and isinstance(item["location"], (list, tuple)) and len(item["location"]) == 2:
                            loc = (int(item["location"][0]), int(item["location"][1]))
                        issues.append(Issue(
                            type=item["type"],
                            message=item["message"],
                            location=loc,
                            suggestion=item.get("suggestion")
                        ))
        except (json.JSONDecodeError, AttributeError, KeyError, ValueError) as e:
            logger.debug("Failed to parse LLM response: %s", e)
            
        return issues