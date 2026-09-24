"""
Tests for audit pipeline.
"""

import pytest
from unittest.mock import patch
from src.audit.pipeline import AuditPipeline
from src.audit.static_rules import Issue as StaticIssue
from src.audit.unified_llm_auditor import Issue as UnifiedIssue


def test_pipeline_static_only():
    """静的ルールのみで問題が解決できるケース"""
    pipeline = AuditPipeline()
    
    # 静的ルールで検出されるが、LLM不要なほど軽微な問題を含むテキスト
    # 例えば、段落数が1つ少ない程度の問題
    text = ""  # 0段落 → 段落数不足の問題
    
    issues = pipeline.run(text)
    
    # 段落数不足の問題が検出されるはず
    assert any(issue.type == "paragraph_count_insufficient" for issue in issues)
    # LLMオーディターは呼ばれず、静的ルールの問題のみが返されるはず
    # 実際の実装では、この判定はパイプラインのロジックに依存する


def test_pipeline_llm_needed():
    """LLMオーディターが必要なケース"""
    pipeline = AuditPipeline()
    
    # 静的ルールでは問題がないが、LLMオーディターでは問題があるテキスト
    # 実際のテストではモックを使う
    with patch.object(pipeline.static_auditor, 'audit') as mock_static_audit:
        with patch.object(pipeline.llm_auditor, 'audit') as mock_llm_audit:
            # 静的ルールオーディターは空のリストを返す（問題なし）
            mock_static_audit.return_value = []
            # LLMオーディターは問題を検出する
            mock_llm_audit.return_value = [
                UnifiedIssue(type="plot_inconsistency", message="プロットに矛盾があります", location=None)
            ]
            
            # カスタムテキスト（中身はモックによって置き換えられるので何でもいい）
            text = "どんなテキストでもいい"
            issues = pipeline.run(text)
            
            # LLMオーディターの問題が結果に含まれるはず
            assert len(issues) == 1
            assert issues[0].type == "plot_inconsistency"
            assert issues[0].message == "プロットに矛盾があります"
            
            # 静的ルールオーディターが呼ばれたことを確認
            mock_static_audit.assert_called_once_with(text)
            # LLMオーディターが呼ばれたことを確認
            mock_llm_audit.assert_called_once_with(text)


def test_pipeline_both_needed():
    """両方のオーディターが必要なケース"""
    pipeline = AuditPipeline()
    
    # 静的ルールオーディターとLLMオーディターの両方が問題を検出するケース
    with patch.object(pipeline.static_auditor, 'audit') as mock_static_audit:
        with patch.object(pipeline.llm_auditor, 'audit') as mock_llm_audit:
            # 静的ルールオーディターは段落数不足を検出
            mock_static_audit.return_value = [
                StaticIssue(type="paragraph_count_insufficient", message="段落数が不足しています", location=None)
            ]
            # LLMオーディターはプロットの矛盾を検出
            mock_llm_audit.return_value = [
                UnifiedIssue(type="plot_inconsistency", message="プロットに矛盾があります", location=None)
            ]
            
            text = "サンプルテキスト"
            issues = pipeline.run(text)
            
            # 両方の問題が結果に含まれるはず
            assert len(issues) == 2
            
            # 種類でソートして比較しやすくする
            issue_types = sorted([issue.type for issue in issues])
            assert issue_types == ["paragraph_count_insufficient", "plot_inconsistency"]
            
            # 両方のオーディターが呼ばれたことを確認
            mock_static_audit.assert_called_once_with(text)
            mock_llm_audit.assert_called_once_with(text)