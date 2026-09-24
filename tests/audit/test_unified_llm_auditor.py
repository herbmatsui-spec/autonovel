"""
Tests for unified LLM auditor.
"""

import pytest
from unittest.mock import patch
from src.audit.unified_llm_auditor import UnifiedLLMAuditor, Issue


@patch("src.audit.unified_llm_auditor.call_llm_api")
def test_audit_returns_issues(mock_call_llm):
    """LLMがIssueのリストを返した場合、それを正しくパースする"""
    # モックの設定
    mock_call_llm.return_value = '[{"type": "plot_inconsistency", "message": "プロットに矛盾があります"}]'
    
    # オーディターを作成して監査を実行
    auditor = UnifiedLLMAuditor()
    issues = auditor.audit("サンプルテキスト")
    
    # 結果を検証
    assert len(issues) == 1
    assert issues[0].type == "plot_inconsistency"
    assert issues[0].message == "プロットに矛盾があります"


@patch("src.audit.unified_llm_auditor.call_llm_api")
def test_audit_empty_when_no_issues(mock_call_llm):
    """LLMが空の配列を返した場合、Issueリストが空になる"""
    mock_call_llm.return_value = '[]'
    
    auditor = UnifiedLLMAuditor()
    issues = auditor.audit("問題のないテキスト")
    
    assert len(issues) == 0


@patch("src.audit.unified_llm_auditor.call_llm_api")
def test_audit_handles_malformed_json(mock_call_llm):
    """LLMが不正なJSONを返した場合のエラーハンドリング"""
    mock_call_llm.return_value = 'これはJSONではない'
    
    auditor = UnifiedLLMAuditor()
    issues = auditor.audit("サンプルテキスト")
    
    # 不正なJSONの場合は空のリストを返すか、または適切にエラーを扱うべき
    # 実装次第だが、ここでは例外が発生しないことを期待
    assert isinstance(issues, list)


def test_audit_requires_text():
    """空のテキストでもオーディターは動作することを確認"""
    auditor = UnifiedLLMAuditor()
    # 例外が発生しないことを確認
    issues = auditor.audit("")
    assert isinstance(issues, list)