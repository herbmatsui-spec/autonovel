"""
オーディターパイプライン - 静的ルールオーディターと統合LLMオーディターを連携
"""

from typing import List
from src.audit.static_rules import StaticRuleAuditor, Issue as StaticIssue
from src.audit.unified_llm_auditor import UnifiedLLMAuditor, Issue as UnifiedIssue


class AuditPipeline:
    """オーディターパイプライン - 静的ルール → LLM → 局所パッチ判定"""
    
    def __init__(self):
        """パイプラインを初期化"""
        self.static_auditor = StaticRuleAuditor()
        self.llm_auditor = UnifiedLLMAuditor()
        
    def run(self, text: str) -> List[UnifiedIssue]:
        """
        テキストに対してパイプラインベースの監査を実行
        
        Args:
            text: 評価対象のテキスト
            
        Returns:
            List[Issue]: すべてのオーディターからの問題のリスト
        """
        # Step 1: 静的ルールオーディターを最初に実行
        static_issues = self.static_auditor.audit(text)
        
        # Step 2: 重大な問題がない場合のみLLMオーディターへ
        # ここでの「重大な問題」の判定は実装次第
        # 現状では簡易的に、文字数超過などの致命的エラーがないかをチェック
        has_critical_issues = self._has_critical_issues(static_issues)
        
        llm_issues = []
        if not has_critical_issues:
            # 重大な問題がない場合のみLLMオーディターを実行
            llm_issues = self.llm_auditor.audit(text)
        # 注意: 実際の最適化では、特定の種類の問題のみをチェックしたり、
        # 問題の数や重大度に基づいて判定する可能性がある
        
        # Step 3: 結果を結合
        # 静的ルールのIssueとLLMのIssueを結合する
        # Issueクラスは共通のものを使うか、変換が必要
        # 現状では両方のIssueクラスが似ているが、別々に定義されているため、
        # ここで統一する必要がある
        
        # 簡易実装：すべてを統合LLMオーディターのIssue形式に変換して返す
        all_issues = []
        
        # 静的ルールのIssueを変換
        for static_issue in static_issues:
            all_issues.append(UnifiedIssue(
                type=static_issue.type,
                message=static_issue.message,
                location=static_issue.location,
                suggestion=static_issue.suggestion
            ))
        
        # LLMオーディターのIssueを追加
        all_issues.extend(llm_issues)
        
        return all_issues
        
    def _has_critical_issues(self, issues: List[StaticIssue]) -> bool:
        """
        致命的な問題があるかどうかを判定
        LLMオーディターをスキップすべき重大な問題がある場合Trueを返す
        """
        # 現状の実装では、文字数超過などの明らかなフォーマットエラーを
        # 致命的とみなすが、これは要件に応じて調整すべき
        critical_types = {"length_exceeded", "title_length_exceeded"}
        
        for issue in issues:
            if issue.type in critical_types:
                return True
                
        return False